from typing import Optional

from sphinx import addnodes
from sphinx.util.typing import OptionSpec

from talondoc.registry.entries.abc import GroupEntry, ListEntry

from ...util.typing import optional_str
from . import TalonDocObjectDescription


class TalonListDirective(TalonDocObjectDescription):
    has_content = True
    required_arguments = 1
    option_spec: OptionSpec = {
        "caption": optional_str,
    }
    final_argument_whitespace = False

    def get_signatures(self):
        return self.arguments[0]

    def find_list(self, sig: str) -> GroupEntry[ListEntry]:
        list_group: Optional[GroupEntry[ListEntry]] = self.talon.registry.lookup(
            "list", sig
        )
        if list_group:
            return list_group
        else:
            raise ValueError(f"Signature '{sig}' matched no lists.")

    def handle_signature(self, sig: str, signode: addnodes.desc_signature):
        list_group = self.find_list(sig)
        self.handle_list(
            list_group,
            signode,
            registry=self.talon.registry,
            include_script=self.options.get("caption", False),
        )
        return list_group.get_name()
