import sys
from typing import ClassVar

from docutils import nodes
from sphinx import addnodes
from sphinx.util.typing import OptionSpec

from ...._util.logging import getLogger
from ..._util.addnodes import bullet_list
from ..._util.typing import flag, optional_str, optional_strlist
from .abc import TalonDocCommandListDescription

_LOGGER = getLogger(__name__)


class TalonCommandHListDirective(TalonDocCommandListDescription):
    has_content = False
    required_arguments = 0
    optional_arguments = sys.maxsize

    option_spec: ClassVar[OptionSpec] = {  # type: ignore
        "context": optional_strlist,
        "contexts": optional_strlist,
        "always_include_script": flag,
        "caption": optional_str,
        "include": optional_strlist,
        "exclude": optional_strlist,
        "columns": int,
    }
    final_argument_whitespace = False

    def run(self) -> list[nodes.Node]:
        fulllist = [
            self.describe_command(
                command,
                addnodes.desc_signature(),
                always_include_script=self.always_include_script,
                docstring_hook=self.docstring_hook,
            )
            for command in self.commands
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
