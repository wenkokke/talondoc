import sys
from typing import TYPE_CHECKING, Any, Optional, cast

from docutils import nodes
from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.util.typing import OptionSpec
from talonfmt.main import talonfmt
from tree_sitter_talon.re import compile

from ...types import CommandEntry
from ...util.typing import flag, optional_str

if TYPE_CHECKING:
    from talondoc.sphinx.domains import TalonDomain
else:
    TalonDomain = Any


class TalonCommandDirective(ObjectDescription):

    has_content = True
    required_arguments = 1
    optional_arguments = sys.maxsize
    option_spec: OptionSpec = {
        "script": flag,
    }
    final_argument_whitespace = False

    @property
    def talon(self) -> TalonDomain:
        return cast(TalonDomain, self.env.get_domain("talon"))

    def get_signatures(self):
        return [" ".join(self.arguments)]

    def find_command(self, sig: str) -> CommandEntry:
        command: Optional[CommandEntry] = None
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
