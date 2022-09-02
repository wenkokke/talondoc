import sys
import typing

from docutils import nodes
from sphinx import addnodes
from sphinx.util.typing import OptionSpec
from talonfmt.main import talonfmt
from tree_sitter_talon.re import compile

from ...entries import CommandEntry
from ...util.typing import flag
from .abc.talon import TalonObjectDescription


class TalonCommandDirective(TalonObjectDescription):

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
            pattern = compile(candidate.ast.rule, captures={}, lists={})
            if pattern.fullmatch(sig):
                if __debug__ and command:
                    raise ValueError(f"Signature '{sig}' matched multiple commands.")
                command = candidate
                if not __debug__:
                    break
        if command:
            return command
        else:
            raise ValueError(f"Signature '{sig}' matched no commands.")

    def handle_rule(self, command: CommandEntry, signode) -> None:
        signode += addnodes.desc_name(text=talonfmt(command.ast.rule, safe=False))

    def handle_script(self, command: CommandEntry, signode) -> None:
        if self.options.get("script", False):
            script = nodes.literal_block()
            script += nodes.Text(talonfmt(command.ast.script, safe=False))
            signode += script

    def handle_signature(self, sig: str, signode):
        command = self.find_command(sig)
        self.handle_rule(command, signode)
        self.handle_script(command, signode)
        return command.name
