import sys
import typing

from sphinx import addnodes
from sphinx.util.typing import OptionSpec

from ...analyze.entries import CommandEntry
from ...util.logging import getLogger
from ...util.typing import flag
from .core import TalonDocObjectDescription, handle_command, include_command

_logger = getLogger(__name__)


class TalonCommandDirective(TalonDocObjectDescription):

    has_content = True
    required_arguments = 1
    optional_arguments = sys.maxsize
    option_spec: OptionSpec = {"script": flag}
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
        include_script = self.options.get("script", False)
        handle_command(
            command,
            signode,
            registry=self.talon,
            include_script=self.options.get("script", False),
        )
        return command.name
