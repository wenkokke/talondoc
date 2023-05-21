import re
from typing import ClassVar, Iterator, Optional, Sequence, cast

from docutils import nodes
from sphinx import addnodes
from talonfmt import talonfmt
from tree_sitter_talon import TalonComment
from typing_extensions import final

from ...._util.logging import getLogger
from ....analysis.registry import data
from ....description import InvalidInterpolation
from ....description.describer import TalonScriptDescriber
from ....sphinx.directives import TalonDocObjectDescription
from ....sphinx.typing import TalonDocstringHook_Callable
from ..._util.addnodes import desc_content, desc_name, paragraph
from ..errors import AmbiguousSignature, UnmatchedSignature

_LOGGER = getLogger(__name__)


class TalonDocCommandDescription(TalonDocObjectDescription):
    @property
    def contexts(self) -> Optional[Iterator[str]]:
        result = [*self.options.get("context", []), *self.options.get("contexts", [])]
        return iter(result) if result else None

    @property
    def always_include_script(self) -> bool:
        return bool(self.options.get("always_include_script", False))

    @final
    def find_command(
        self,
        text: str,
        *,
        fullmatch: bool = False,
        restrict_to: Optional[Iterator[str]] = None,
    ) -> data.Command:
        commands = list(
            self.find_commands(text, fullmatch=fullmatch, restrict_to=restrict_to)
        )
        if len(commands) == 0:
            raise UnmatchedSignature(self.get_location(), text)
        if len(commands) >= 2:
            raise AmbiguousSignature(
                self.get_location(),
                text,
                [
                    f"{command.location}: {talonfmt(command.rule, safe=False)}"
                    for command in commands
                ],
            )
        return commands[0]

    @final
    def get_commands(
        self,
        *,
        restrict_to: Optional[Iterator[str]] = None,
    ) -> Iterator[data.Command]:
        yield from self.talon.registry.get_commands(restrict_to=restrict_to)

    @final
    def find_commands(
        self,
        text: str,
        *,
        fullmatch: bool = False,
        restrict_to: Optional[Iterator[str]] = None,
    ) -> Iterator[data.Command]:
        _LOGGER.debug(
            f"searching for commands matching '{text}' (restricted by {restrict_to})"
        )
        yield from self.talon.registry.find_commands(
            self._split_phrase(text),
            fullmatch=fullmatch,
            restrict_to=restrict_to,
        )

    _RE_WHITESPACE: ClassVar[re.Pattern[str]] = re.compile(r"\s+")

    @final
    def _split_phrase(self, text: str) -> Sequence[str]:
        return self.__class__._RE_WHITESPACE.split(text)

    @final
    def describe_command(
        self,
        command: data.Command,
        signode: addnodes.desc_signature,
        *,
        always_include_script: bool,
        docstring_hook: Optional[TalonDocstringHook_Callable],
    ) -> addnodes.desc_signature:
        signode += desc_name(self.describe_rule(command.rule))
        signode += desc_content(
            *self.describe_script(
                command,
                always_include_script=always_include_script,
                docstring_hook=docstring_hook,
            )
        )
        return signode

    @final
    def describe_script(
        self,
        command: data.Command,
        *,
        always_include_script: bool,
        docstring_hook: Optional[TalonDocstringHook_Callable],
    ) -> Sequence[nodes.Element]:
        """
        Describe the script using the docstrings on the script, the docstrings on
        the actions, or finally by including it as a code block.
        """
        buffer = []

        # 1. Use the Talon docstrings in the command script. Talon docstrings are comments which start with ###.
        desc = self._try_describe_script_with_script_docstrings(command)

        # 2. Use the Python docstrings from the actions used in the command script.
        if desc is None:
            desc = self._try_describe_script_with_action_docstrings(
                command, docstring_hook=docstring_hook
            )

        # Append the description.
        if desc is not None:
            buffer.append(paragraph(nodes.Text(str(desc))))

        if desc is None or always_include_script:
            # 3. Include the command script.
            buffer.append(self._describe_script_with_script(command))

        return buffer

    @final
    def _try_describe_script_with_script_docstrings(
        self,
        command: data.Command,
    ) -> Optional[nodes.Text]:
        """
        Describe the script using the docstrings present in the script itself.
        """
        comments = []
        for child in command.script.children:
            if isinstance(child, TalonComment):
                comment = child.text.strip()
                if comment.startswith("###"):
                    comments.append(comment.removeprefix("###").strip())
        if comments:
            return nodes.Text(" ".join(comments))
        else:
            return None

    @final
    def _try_describe_script_with_action_docstrings(
        self,
        command: data.Command,
        *,
        docstring_hook: Optional[TalonDocstringHook_Callable],
    ) -> Optional[nodes.Text]:
        """
        Describe the script using the docstrings on the actions used by the script.
        """
        try:
            describer = TalonScriptDescriber(
                self.talon.registry, docstring_hook=docstring_hook
            )
            desc = describer.describe(command.script)
            if desc:
                return nodes.Text(str(desc))
        except InvalidInterpolation as e:
            _LOGGER.exception(e)
        return None

    @final
    def _describe_script_with_script(
        self, command: data.Command
    ) -> nodes.literal_block:
        """
        Describe the script by including it as a code block.
        """
        code = talonfmt(command.script, safe=False)
        literal_block = nodes.literal_block(code, code)
        literal_block["language"] = "python"
        return literal_block


class TalonDocCommandListDescription(TalonDocCommandDescription):
    @property
    def caption(self) -> str:
        # Get caption from options or from file name
        return cast(str, self.options.get("caption", None) or ".".join(self.arguments))

    @property
    def include(self) -> Sequence[Sequence[str]]:
        return tuple(
            self._split_phrase(phrase) for phrase in self.options.get("include", ())
        )

    @property
    def exclude(self) -> Sequence[Sequence[str]]:
        return tuple(
            self._split_phrase(phrase) for phrase in self.options.get("exclude", ())
        )

    @property
    def columns(self) -> int:
        return cast(int, self.options.get("columns", 2))

    @property
    def commands(self) -> Iterator[data.Command]:
        for command in self.get_commands(restrict_to=self.contexts):
            if self._should_include(command.rule):
                yield command

    def _should_include(
        self,
        rule: data.Rule,
        *,
        fullmatch: bool = False,
    ) -> bool:
        # If both :include: and :exclude:
        # Does command match :include: and not match :exclude:?
        # If :include: but no :exclude:
        # Does command match :include:?
        # If :exclude: but no :include:
        # Does command not match exclude?
        _should_include = self._matches_include(rule, fullmatch=fullmatch)
        _should_exclude = self._matches_exclude(rule, fullmatch=fullmatch)
        return _should_include and not _should_exclude

    @final
    def _matches_include(
        self,
        rule: data.Rule,
        *,
        fullmatch: bool = False,
    ) -> bool:
        return self._match_any_of(rule, self.include, default=True, fullmatch=fullmatch)

    @final
    def _matches_exclude(
        self,
        rule: data.Rule,
        *,
        fullmatch: bool = False,
    ) -> bool:
        return self._match_any_of(
            rule, self.exclude, default=False, fullmatch=fullmatch
        )

    @final
    def _match_any_of(
        self,
        rule: data.Rule,
        phrases: Sequence[Sequence[str]],
        *,
        default: bool,
        fullmatch: bool = False,
    ) -> bool:
        return any(
            self.talon.registry.match(phrase, rule, fullmatch=fullmatch)
            for phrase in phrases
        )
