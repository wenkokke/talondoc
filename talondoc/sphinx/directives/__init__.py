from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any, Optional, Union, cast

import sphinx.directives
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

from ...analyze.entries import CommandEntry, PackageEntry, TalonFileEntry
from ...analyze.registry import Registry
from ...util.desc import InvalidInterpolation
from ...util.describer import TalonScriptDescriber
from ...util.logging import getLogger
from ...util.nodes import desc_content, desc_name, paragraph

_logger = getLogger(__name__)

if TYPE_CHECKING:
    from talondoc.sphinx.domains import TalonDomain
else:
    TalonDomain = Any


class TalonDocDirective(sphinx.directives.SphinxDirective):
    @property
    def talon(self) -> TalonDomain:
        return cast(TalonDomain, self.env.get_domain("talon"))


class TalonDocObjectDescription(sphinx.directives.ObjectDescription, TalonDocDirective):
    pass


def include_command(
    candidate: CommandEntry,
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
    pattern = candidate.ast.rule.to_pattern(captures=captures, lists=lists)

    def match(sig: str) -> bool:
        return bool(pattern.fullmatch(sig) if fullmatch else pattern.match(sig))

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


def describe_rule(command: CommandEntry) -> nodes.Text:
    return nodes.Text(talonfmt(command.ast.rule, safe=False))


def try_describe_script_via_action_docstrings(
    command: CommandEntry,
    *,
    registry: Registry,
    docstring_hook: Optional[Callable[[str], Optional[str]]],
) -> Optional[nodes.Text]:
    """
    Describe the script using the docstrings on the actions used by the script.
    """
    try:
        describer = TalonScriptDescriber(
            registry, docstring_hook=docstring_hook
        )
        desc = describer.describe(command.ast)
        if desc:
            return nodes.Text(str(desc))
    except InvalidInterpolation as e:
        _logger.exception(e)
    return None


def try_describe_script_via_script_docstrings(
    command: CommandEntry,
) -> Optional[nodes.Text]:
    """
    Describe the script using the docstrings present in the script itself.
    """
    comments = []
    children = [*command.ast.children, *command.ast.script.children]
    for child in children:
        if isinstance(child, TalonComment):
            comment = child.text.strip()
            if comment.startswith("###"):
                comments.append(comment.removeprefix("###").strip())
    if comments:
        return nodes.Text(" ".join(comments))
    else:
        return None


def describe_script_via_code_block(command: CommandEntry) -> addnodes.highlightlang:
    """
    Describe the script by including it as a code block.
    """
    code = talonfmt(command.ast.script, safe=False)
    literal_block = nodes.literal_block(code, code)
    literal_block["language"] = "python"
    return literal_block  # type: ignore


def describe_script(
    command: CommandEntry,
    *,
    registry: Registry,
    docstring_hook: Optional[Callable[[str], Optional[str]]],
    include_script: bool,
) -> list[nodes.Element]:
    """
    Describe the script using the docstrings on the script, the docstrings on
    the actions, or finally by including it as a code block.
    """
    desc = try_describe_script_via_script_docstrings(command)
    desc = desc or try_describe_script_via_action_docstrings(
        command, registry=registry, docstring_hook=docstring_hook
    )
    buffer = []
    if desc:
        buffer.append(paragraph(nodes.Text(desc)))
    if not desc or include_script:
        buffer.append(describe_script_via_code_block(command))
    return buffer


def handle_command(
    command: CommandEntry,
    signode: addnodes.desc_signature,
    *,
    registry: Registry,
    docstring_hook: Optional[Callable[[str], Optional[str]]],
    include_script: bool,
) -> addnodes.desc_signature:
    signode += desc_name(describe_rule(command))
    signode += desc_content(
        *describe_script(
            command,
            registry=registry,
            docstring_hook=docstring_hook,
            include_script=include_script,
        )
    )
    return signode


def describe_command(
    command: CommandEntry,
    *,
    registry: Registry,
    docstring_hook: Optional[Callable[[str], Optional[str]]],
    include_script: bool,
) -> addnodes.desc_signature:
    return handle_command(
        command,
        addnodes.desc_signature(),
        registry=registry,
        docstring_hook=docstring_hook,
        include_script=include_script,
    )


class TalonCommandListDirective(TalonDocDirective):
    def find_package(self) -> PackageEntry:
        namespace = self.options.get("package")
        candidate = self.talon.registry.latest_package
        if candidate and (not namespace or candidate.namespace == namespace):
            return candidate
        candidate = self.talon.registry.packages.get(namespace, None)
        if candidate:
            return candidate
        raise ValueError(f"Could not find package '{namespace}'")

    def find_file(
        self, sig: str, *, package_entry: Optional[PackageEntry] = None
    ) -> TalonFileEntry:
        # Find the package:
        if package_entry is None:
            try:
                package_entry = self.find_package()
            except ValueError as e:
                raise ValueError(f"Could not find file '{sig}'", e)

        # Find the file:
        for file in package_entry.files:
            if isinstance(file, TalonFileEntry):
                if (
                    sig == file.name
                    or sig == str(file.path)
                    or f"{sig}.talon" == file.name
                    or f"{sig}.talon" == str(file.path)
                ):
                    return file
        raise ValueError(f"Could not find file '{sig}'.")

    def find_commands(self) -> Iterator[CommandEntry]:
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
            yield file.name.removesuffix(".talon")
            return
