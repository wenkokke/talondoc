import itertools
import re
import sys
from collections.abc import Callable, Iterator
from typing import List, Optional, Sequence, Union

from docutils import nodes
from sphinx import addnodes
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
from typing_extensions import Literal, override

from talondoc.sphinx.directives import TalonDocDirective
from talondoc.sphinx.directives.util import (
    find_file,
    find_package,
    resolve_files,
    resolve_packages,
)

from ....registry import Registry
from ....registry.entries.user import (
    UserCommandEntry,
    UserPackageEntry,
    UserTalonFileEntry,
)
from ....sphinx.typing import TalonDocstringHook_Callable
from ....util.desc import InvalidInterpolation
from ....util.describer import TalonScriptDescriber
from ....util.logging import getLogger
from ....util.nodes import desc_content, desc_name, paragraph

_LOGGER = getLogger(__name__)

_RE_WHITESPACE = re.compile(r"\s+")


def include_command(
    candidate: UserCommandEntry,
    sig: Optional[str] = None,
    *,
    fullmatch: bool = True,
    default: Literal["include", "exclude"] = "include",
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
                    get_capture=captures,
                    get_list=lists,
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


def describe_rule(command: UserCommandEntry) -> nodes.Text:
    return nodes.Text(talonfmt(command.ast.left, safe=False))


def try_describe_script_via_action_docstrings(
    command: UserCommandEntry,
    *,
    registry: Registry,
    docstring_hook: Optional[TalonDocstringHook_Callable],
) -> Optional[nodes.Text]:
    """
    Describe the script using the docstrings on the actions used by the script.
    """
    try:
        describer = TalonScriptDescriber(registry, docstring_hook=docstring_hook)
        desc = describer.describe(command.ast)
        if desc:
            return nodes.Text(str(desc))
    except InvalidInterpolation as e:
        _LOGGER.exception(e)
    return None


def try_describe_script_via_script_docstrings(
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


def describe_script_via_code_block(command: UserCommandEntry) -> addnodes.highlightlang:
    """
    Describe the script by including it as a code block.
    """
    code = talonfmt(command.ast.script, safe=False)
    literal_block = nodes.literal_block(code, code)
    literal_block["language"] = "python"
    return literal_block  # type: ignore


def describe_script(
    command: UserCommandEntry,
    *,
    registry: Registry,
    include_script: bool,
    docstring_hook: Optional[TalonDocstringHook_Callable],
) -> list[nodes.Element]:
    """
    Describe the script using the docstrings on the script, the docstrings on
    the actions, or finally by including it as a code block.
    """
    buffer = []

    # 1. Use the Talon docstrings in the command script. Talon docstrings are comments which start with ###.
    desc = try_describe_script_via_script_docstrings(command)

    # 2. Use the Python docstrings from the actions used in the command script.
    if desc is None:
        desc = try_describe_script_via_action_docstrings(
            command, registry=registry, docstring_hook=docstring_hook
        )

    # Append the description.
    if desc is not None:
        buffer.append(paragraph(nodes.Text(str(desc))))

    if desc is None or include_script:
        # 3. Include the command script.
        buffer.append(describe_script_via_code_block(command))

    return buffer


def describe_command(
    command: UserCommandEntry,
    signode: addnodes.desc_signature,
    *,
    registry: Registry,
    include_script: bool,
    docstring_hook: Optional[TalonDocstringHook_Callable],
) -> addnodes.desc_signature:
    signode += desc_name(describe_rule(command))
    signode += desc_content(
        *describe_script(
            command,
            registry=registry,
            include_script=include_script,
            docstring_hook=docstring_hook,
        )
    )
    return signode


def resolve_contexts(
    registry: Registry,
    contexts: Sequence[Union[str, UserTalonFileEntry]] = (),
    *,
    packages: Sequence[Union[str, UserPackageEntry]] = (),
) -> Sequence[UserTalonFileEntry]:
    buffer = []
    for file in resolve_files(registry, contexts, packages=packages):
        if isinstance(file, UserTalonFileEntry):
            buffer.append(file)
        else:
            raise ValueError(f"Context '{file}' does not match a .talon file.")
    return buffer


def find_commands(
    registry: Registry,
    *,
    packages: Sequence[Union[str, UserPackageEntry]] = (),
    contexts: Sequence[Union[str, UserTalonFileEntry]] = (),
) -> Iterator[UserCommandEntry]:
    packages = resolve_packages(registry, packages)
    contexts = resolve_contexts(registry, contexts, packages=packages)
    if contexts:
        for context in contexts:
            yield from context.commands
    else:
        for command in registry.commands:
            yield command


class TalonCommandListDirective(TalonDocDirective):
    def find_commands(self) -> Iterator[UserCommandEntry]:
        packages = self.options.get("package", [])
        contexts = list(
            itertools.chain(self.arguments, self.options.get("context", []))
        )

        # If contexts were provided, return all commands in that context which
        # have not been explicitly excluded. Otherwise return all commands that
        # have been explicitly included:
        default: Literal["include", "exclude"] = self.options.get(
            "default", "include" if contexts else "exclude"
        )
        exclude = self.options.get("exclude", ())
        include = self.options.get("include", ())

        for command in find_commands(
            self.talon.registry,
            packages=packages,
            contexts=contexts,
        ):
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
            file = find_file(self.talon.registry, self.arguments[0])
            yield file.get_name().removesuffix(".talon")
            return
