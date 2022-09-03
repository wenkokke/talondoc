import sys
import typing

from docutils import nodes
from sphinx import addnodes
from sphinx.util.typing import OptionSpec
from talonfmt.main import talonfmt
from tree_sitter_talon import TalonComment
from tree_sitter_talon.re import compile

from ...analyze.registry import Registry
from ...entries import CommandEntry
from ...util.desc import InvalidInterpolation
from ...util.describer import TalonScriptDescriber
from ...util.logging import getLogger
from ...util.typing import flag
from ...util.nodes import desc_name, desc_content
from .abc import TalonDocObjectDescription

_logger = getLogger(__name__)


def include_command(
    candidate: CommandEntry,
    sig: typing.Optional[str] = None,
    *,
    fullmatch: bool = True,
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
    captures: dict[str, str] = {},
    lists: dict[str, str] = {},
):
    pattern = compile(candidate.ast.rule, captures=captures, lists=lists)

    def match(sig: str) -> bool:
        return bool(pattern.fullmatch(sig) if fullmatch else pattern.match(sig))

    return (not sig or match(sig)) and (
        not exclude
        or not any(match(exclude_sig) for exclude_sig in exclude)
        or any(match(include_sig) for include_sig in include)
    )


def describe_rule(command: CommandEntry) -> nodes.Text:
    return nodes.Text(talonfmt(command.ast.rule, safe=False))


def try_describe_command_auto(
    command: CommandEntry, *, registry: Registry
) -> typing.Optional[nodes.Text]:
    try:
        describer = TalonScriptDescriber(registry)
        desc = describer.describe(command.ast)
        if desc:
            return nodes.Text(desc.compile())
    except InvalidInterpolation as e:
        _logger.exception(e)
    return None


def try_describe_command_via_docstring(
    command: CommandEntry,
) -> typing.Optional[nodes.Text]:
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


def describe_command_via_script(command: CommandEntry) -> nodes.Element:
    script = nodes.literal_block()
    script["classes"].append("code")
    script += nodes.Text(talonfmt(command.ast.script, safe=False))
    return script  # type: ignore


def describe_command(command: CommandEntry, *, registry: Registry) -> nodes.Element:
    desc = try_describe_command_via_docstring(command)
    desc = desc or try_describe_command_auto(command, registry=registry)
    if desc:
        paragraph = nodes.paragraph()
        paragraph += nodes.Text(desc)
        return paragraph  # type: ignore
    else:
        return describe_command_via_script(command)


class TalonCommandDirective(TalonDocObjectDescription):

    has_content = True
    required_arguments = 1
    optional_arguments = sys.maxsize
    option_spec: OptionSpec = {
        "script": flag,
    }
    final_argument_whitespace = False

    def get_signatures(self):
        return [" ".join(self.arguments)]

    def find_command(self, sig: str) -> CommandEntry:
        command: typing.Optional[CommandEntry] = None
        for candidate in self.talon.commands:
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
        signode += desc_name(describe_rule(command))
        signode += desc_content(describe_command(command, registry=self.talon))
        return command.name
