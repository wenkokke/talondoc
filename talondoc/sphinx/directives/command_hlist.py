import sys

from docutils import nodes
from sphinx import addnodes
from sphinx.util.typing import OptionSpec

from ...util.logging import getLogger
from ...util.nodes import bullet_list
from ...util.typing import optional_str, optional_strlist
from . import TalonCommandListDirective

_LOGGER = getLogger(__name__)


class TalonCommandHListDirective(TalonCommandListDirective):
    has_content = False
    required_arguments = 0
    optional_arguments = sys.maxsize
    option_spec: OptionSpec = {
        "package": optional_str,
        "caption": optional_str,
        "default": optional_str,
        "include": optional_strlist,
        "exclude": optional_strlist,
        "columns": int,
    }
    final_argument_whitespace = False

    def run(self) -> list[nodes.Node]:
        ncolumns = self.options.get("columns", 2)
        fulllist = [
            self.describe_command(
                command,
                registry=self.talon.registry,
                include_script=False,
            )
            for command in self.find_commands()
        ]
        # create a hlist node where the items are distributed
        # (source: sphinx.directives.other.HList)
        npercol, nmore = divmod(len(fulllist), ncolumns)
        index = 0
        hlist = addnodes.hlist()
        hlist["ncolumns"] = str(ncolumns)
        for column in range(ncolumns):
            endindex = index + ((npercol + 1) if column < nmore else npercol)
            hlist += addnodes.hlistcol("", bullet_list(*fulllist[index:endindex]))
            index = endindex
        return [hlist]
