import sys
from typing import List, Optional

from sphinx import addnodes
from sphinx.util.typing import OptionSpec
from talonfmt import talonfmt
from typing_extensions import override

from talondoc.sphinx.directives.command.util import (
    describe_command,
    find_commands,
    include_command,
)
from talondoc.sphinx.directives.errors import AmbiguousSignature, UnmatchedSignature

from ....registry.entries.user import UserCommandEntry
from ....sphinx.directives import TalonDocObjectDescription
from ....util.logging import getLogger
from ....util.typing import flag, optional_strlist

_LOGGER = getLogger(__name__)


class TalonCommandDirective(TalonDocObjectDescription):
    has_content = True
    required_arguments = 1
    optional_arguments = sys.maxsize
    option_spec: OptionSpec = {
        "package": optional_strlist,
        "context": optional_strlist,
        "include_script": flag,
    }
    final_argument_whitespace = False

    @override
    def get_signatures(self) -> List[str]:
        sig = " ".join(self.arguments)
        return [sig]

    @override
    def handle_signature(self, sig: str, signode: addnodes.desc_signature):
        try:
            command = self.find_command(sig)
            include_script = self.options.get("include_script", False)
            describe_command(
                command,
                signode,
                registry=self.talon.registry,
                include_script=include_script,
                docstring_hook=self.docstring_hook,
            )
            return command.get_name()
        except (UnmatchedSignature, AmbiguousSignature) as e:
            _LOGGER.error(e)
            raise ValueError(e)

    def find_command(self, sig: str) -> UserCommandEntry:
        packages = self.options.get("package", [])
        contexts = self.options.get("context", [])
        commands = [
            command
            for command in find_commands(
                self.talon.registry, contexts=contexts, packages=packages
            )
            if include_command(command, sig, fullmatch=True)
        ]
        if len(commands) == 0:
            raise UnmatchedSignature(self.get_location(), sig)
        if len(commands) > 1:
            raise AmbiguousSignature(
                self.get_location(),
                sig,
                [
                    f"{command.get_location()}: {talonfmt(command.ast.left, safe=False)}"
                    for command in commands
                ],
            )
        return commands[0]
