import re
import sys
from collections.abc import Callable, Iterator
from typing import Optional, Union

from docutils import nodes
from sphinx import addnodes
from sphinx.util.typing import OptionSpec
from talonfmt import talonfmt
from tree_sitter_talon import (
    TalonCapture,
    TalonChoice,
    TalonComment,
    TalonEndAnchor,
    TalonList,
    TalonOptional,
    TalonParenthesizedRule,
    TalonRepeat,
    TalonRepeat1,
    TalonRule,
    TalonSeq,
    TalonStartAnchor,
    TalonWord,
)

from talondoc.sphinx.directives import TalonDocDirective, TalonDocObjectDescription

from ....registry import Registry
from ....registry.entries.user import (
    UserCommandEntry,
    UserPackageEntry,
    UserTalonFileEntry,
)
from ....util.desc import InvalidInterpolation
from ....util.describer import TalonScriptDescriber
from ....util.logging import getLogger
from ....util.nodes import desc_content, desc_name, paragraph
from ....util.typing import flag

_LOGGER = getLogger(__name__)


_RE_WHITESPACE = re.compile(r"\s+")


def include_command(
    candidate: UserCommandEntry,
    sig: Optional[str] = None,
    *,
    fullmatch: bool = True,
    default: str = "include",
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
    captures: Optional[
        Callable[
            [str],
            Optional[
                Union[
                    TalonCapture,
                    TalonChoice,
                    TalonEndAnchor,
                    TalonList,
                    TalonOptional,
                    TalonParenthesizedRule,
                    TalonRepeat,
                    TalonRepeat1,
                    TalonRule,
                    TalonSeq,
                    TalonStartAnchor,
                    TalonWord,
                ]
            ],
        ]
    ] = None,
    lists: Optional[Callable[[str], Optional[list[str]]]] = None,
):
    assert default in ["include", "exclude"]

    def match(sig: str) -> bool:
        try:
            words = _RE_WHITESPACE.split(sig)
            return bool(
                candidate.ast.rule.match(
                    words,
                    fullmatch=fullmatch,
                    get_capture=None,
                    get_list=None,
                )
            )
        except IndexError:
            return False

    def excluded() -> bool:
        return (
            bool(exclude)
            and any(match(exclude_sig) for exclude_sig in exclude)
            and not any(match(include_sig) for include_sig in include)
        )

    def included() -> bool:
        return any(match(include_sig) for include_sig in include) and not any(
            match(exclude_sig) for exclude_sig in exclude
        )

    if default == "include":
        return (not sig or match(sig)) and not excluded()
    else:
        return (sig and match(sig)) or included()


class TalonCommandDirective(TalonDocObjectDescription):
    has_content = True
    required_arguments = 1
    optional_arguments = sys.maxsize
    option_spec: OptionSpec = {"script": flag}
    final_argument_whitespace = False

    def get_signatures(self):
        return [" ".join(self.arguments)]

    def find_command(self, sig: str) -> UserCommandEntry:
        command: Optional[UserCommandEntry] = None
        for candidate in self.talon.registry.commands:
            if include_command(candidate, sig, fullmatch=True):
                if __debug__ and command:
                    raise ValueError(f"Signature '{sig}' matched multiple commands.")
                command = candidate
                if not __debug__:
                    break
        if command:
            return command
        else:
            raise ValueError(f"Signature '{sig}' matched no commands.")

    def handle_signature(self, sig: str, signode: addnodes.desc_signature):
        command = self.find_command(sig)
        self.handle_command(
            command,
            signode,
            registry=self.talon.registry,
            include_script=self.options.get("script", False),
        )
        return command.get_name()

    def describe_rule(self, command: UserCommandEntry) -> nodes.Text:
        return nodes.Text(talonfmt(command.ast.left, safe=False))

    def try_describe_script_via_action_docstrings(
        self,
        command: UserCommandEntry,
        *,
        registry: Registry,
    ) -> Optional[nodes.Text]:
        """
        Describe the script using the docstrings on the actions used by the script.
        """
        try:
            describer = TalonScriptDescriber(
                registry, docstring_hook=self.docstring_hook
            )
            desc = describer.describe(command.ast)
            if desc:
                return nodes.Text(str(desc))
        except InvalidInterpolation as e:
            _LOGGER.exception(e)
        return None

    def try_describe_script_via_script_docstrings(
        self,
        command: UserCommandEntry,
    ) -> Optional[nodes.Text]:
        """
        Describe the script using the docstrings present in the script itself.
        """
        comments = []
        for child in command.ast.right.children:
            if isinstance(child, TalonComment):
                comment = child.text.strip()
                if comment.startswith("###"):
                    comments.append(comment.removeprefix("###").strip())
        if comments:
            return nodes.Text(" ".join(comments))
        else:
            return None

    def describe_script_via_code_block(
        self, command: UserCommandEntry
    ) -> addnodes.highlightlang:
        """
        Describe the script by including it as a code block.
        """
        code = talonfmt(command.ast.script, safe=False)
        literal_block = nodes.literal_block(code, code)
        literal_block["language"] = "python"
        return literal_block  # type: ignore

    def describe_script(
        self,
        command: UserCommandEntry,
        *,
        registry: Registry,
        include_script: bool,
    ) -> list[nodes.Element]:
        """
        Describe the script using the docstrings on the script, the docstrings on
        the actions, or finally by including it as a code block.
        """
        buffer = []

        # 1. Use the Talon docstrings in the command script. Talon docstrings are comments which start with ###.
        desc = self.try_describe_script_via_script_docstrings(command)

        # 2. Use the Python docstrings from the actions used in the command script.
        if desc is None:
            desc = self.try_describe_script_via_action_docstrings(
                command, registry=registry
            )

        # Append the description.
        if desc is not None:
            buffer.append(paragraph(nodes.Text(str(desc))))

        if desc is None or include_script:
            # 3. Include the command script.
            buffer.append(self.describe_script_via_code_block(command))

        return buffer

    def handle_command(
        self,
        command: UserCommandEntry,
        signode: addnodes.desc_signature,
        *,
        registry: Registry,
        include_script: bool,
    ) -> addnodes.desc_signature:
        signode += desc_name(self.describe_rule(command))
        signode += desc_content(
            *self.describe_script(
                command,
                registry=registry,
                include_script=include_script,
            )
        )
        return signode

    def describe_command(
        self,
        command: UserCommandEntry,
        *,
        registry: Registry,
        include_script: bool,
    ) -> addnodes.desc_signature:
        return self.handle_command(
            command,
            addnodes.desc_signature(),
            registry=registry,
            include_script=include_script,
        )


class TalonCommandListDirective(TalonDocDirective):
    def find_package(self) -> UserPackageEntry:
        namespace = self.options.get("package")
        candidate = self.talon.registry.active_package_entry
        if candidate and (not namespace or candidate.get_namespace() == namespace):
            return candidate
        candidate = self.talon.registry.packages.get(namespace, None)
        if candidate:
            return candidate
        raise ValueError(f"Could not find package '{namespace}'")

    def find_file(
        self, sig: str, *, package_entry: Optional[UserPackageEntry] = None
    ) -> UserTalonFileEntry:
        # Try lookup with 'sig' as name:
        result = self.talon.registry.lookup("file", sig)
        if result:
            return result

        # Try lookup with 'sig.talon' as name:
        result = self.talon.registry.lookup("file", f"{sig}.talon")
        if result:
            return result

        # Try searching in the active package:
        if package_entry is None:
            try:
                package_entry = self.find_package()
            except ValueError as e:
                raise ValueError(f"Could not find file '{sig}'", e)

        # Find the file:
        for file in package_entry.files:
            if isinstance(file, UserTalonFileEntry):
                # Try comparison with 'sig' as path:
                if sig == str(file.path):
                    return file
                # Try comparison with 'sig.talon' as path:
                if f"{sig}.talon" == str(file.path):
                    return file
        raise ValueError(f"Could not find file '{sig}'.")

    def find_commands(self) -> Iterator[UserCommandEntry]:
        exclude = self.options.get("exclude", ())
        include = self.options.get("include", ())

        if self.arguments:
            # If file arguments were given, return all commands in that file
            # which have not been explicitly excluded:
            for sig in self.arguments:
                default = self.options.get("default", "include")
                for command in self.find_file(sig).commands:
                    if include_command(
                        command, default=default, exclude=exclude, include=include
                    ):
                        yield command
        else:
            # If no file arguments were given, return all commands in the package
            # which have been explicitly included:
            default = self.options.get("default", "exclude")
            for command in self.talon.registry.commands:
                if include_command(
                    command, default=default, exclude=exclude, include=include
                ):
                    yield command

    def caption(self) -> Iterator[str]:
        # Get caption from options
        caption = self.options.get("caption", None)
        if caption:
            yield caption
            return
        # Get caption from file name
        if len(self.arguments) == 1:
            file = self.find_file(self.arguments[0])
            yield file.get_name().removesuffix(".talon")
            return
