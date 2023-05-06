import sys
from typing import Iterator, Optional

from docutils import nodes
from sphinx import addnodes
from sphinx.util.typing import OptionSpec

from ...util.addnodes import bullet_list
from ...util.typing import flag, optional_str, optional_strlist
from .abc import TalonDocCommandDescription


class TalonCommandHListDirective(TalonDocCommandDescription):
    has_content = False
    required_arguments = 0
    optional_arguments = sys.maxsize
    option_spec: OptionSpec = {
        "restrict_to": optional_strlist,
        "always_include_script": flag,
        "caption": optional_str,
        "columns": int,
    }
    final_argument_whitespace = False

    @property
    def caption(self) -> str:
        # Get caption from options
        caption: Optional[str] = self.options.get("caption", None)
        if caption:
            return caption
        # Get caption from file name
        return ".".join(self.arguments)

    @property
    def columns(self) -> int:
        columns: int = self.options.get("columns", 2)
        return columns

    def run(self) -> list[nodes.Node]:
        commands = self.get_commands(restrict_to=self.restrict_to)
        fulllist = [
            self.describe_command(
                command,
                addnodes.desc_signature(),
                always_include_script=self.always_include_script,
                docstring_hook=self.docstring_hook,
            )
            for command in commands
        ]
        # create a hlist node where the items are distributed
        # (source: sphinx.directives.other.HList)
        npercol, nmore = divmod(len(fulllist), self.columns)
        index = 0
        hlist = addnodes.hlist()
        hlist["ncolumns"] = str(self.columns)
        for column in range(self.columns):
            endindex = index + ((npercol + 1) if column < nmore else npercol)
            hlist += addnodes.hlistcol("", bullet_list(*fulllist[index:endindex]))
            index = endindex
        return [hlist]
