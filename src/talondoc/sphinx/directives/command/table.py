import sys
from typing import ClassVar

from docutils import nodes
from sphinx.util.typing import OptionSpec

from ...._util.logging import getLogger
from ..._util.addnodes import (
    colspec,
    entry,
    fragtable,
    row,
    table,
    tbody,
    tgroup,
    title,
)
from ..._util.addnodes.rule import desc_rule
from ..._util.typing import flag, optional_str, optional_strlist
from .abc import TalonDocCommandListDescription

_LOGGER = getLogger(__name__)


class TalonCommandTableDirective(TalonDocCommandListDescription):
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
    }
    final_argument_whitespace = False

    def run(self) -> list[nodes.Node]:
        return [
            fragtable(
                title(nodes.Text(self.caption)),
                tgroup(
                    colspec(colwidth=1),
                    colspec(colwidth=1),
                    tbody(
                        row(
                            entry(desc_rule(command.rule)),
                            entry(
                                *self.describe_script(
                                    command,
                                    always_include_script=self.always_include_script,
                                    docstring_hook=self.docstring_hook,
                                )
                            ),
                        )
                        for command in self.commands
                    ),
                    cols=2,
                ),
                classes="compact",
            )
        ]
