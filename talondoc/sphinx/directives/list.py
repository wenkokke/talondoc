from typing import Optional

from docutils import nodes
from sphinx import addnodes
from sphinx.util.typing import OptionSpec

from talondoc.registry import Registry
from talondoc.registry.entries.abc import GroupEntry, ListEntry

from ...util.nodes import (
    colspec,
    desc_content,
    desc_name,
    entry,
    row,
    table,
    tbody,
    tgroup,
    title,
)
from ...util.typing import optional_str
from . import TalonDocObjectDescription


class TalonListDirective(TalonDocObjectDescription):
    has_content = True
    required_arguments = 1
    option_spec: OptionSpec = {
        "caption": optional_str,
    }
    final_argument_whitespace = False

    def get_signature(self) -> str:
        sig = self.arguments[0]
        if type(sig) == str:
            return sig
        raise TypeError(type(sig))

    def find_list(self, sig: str) -> GroupEntry[ListEntry]:
        if type(sig) == str:
            list_group = self.talon.registry.lookup("list", sig)
            if list_group:
                return list_group
            else:
                raise ValueError(f"Signature '{sig}' matched no lists.")
        else:
            raise TypeError(type(sig))

    def handle_signature(self, sig: str, signode: addnodes.desc_signature):
        list_group = self.find_list(sig)
        self.handle_list(
            list_group,
            signode,
            caption=self.options.get("caption", None),
        )
        return list_group.get_name()

    def handle_list(
        self,
        list_group: GroupEntry[ListEntry],
        signode: addnodes.desc_signature,
        *,
        caption: Optional[str],
    ) -> addnodes.desc_signature:
        signode += desc_name(nodes.Text(list_group.get_name()))
        signode += desc_content()
        return signode
        ...
        # list_group = self.find_list(self.get_signature())
        # list_value = list_group.default.get_value()
        # if list_value:
        #     return [
        #         table(
        #             *[title(nodes.Text(caption)) for caption in self.caption()],
        #             tgroup(
        #                 colspec(colwidth=1),
        #                 colspec(colwidth=1),
        #                 tbody(
        #                     row(
        #                         entry(self.describe_rule(command)),
        #                         entry(
        #                             *self.describe_script(
        #                                 command,
        #                                 registry=self.talon.registry,
        #                                 include_script=False,
        #                             )
        #                         ),
        #                     )
        #                     for command in clist_value
        #                 ),
        #                 cols=2,
        #             ),
        #             classes="compact",
        #         )
        #     ]
