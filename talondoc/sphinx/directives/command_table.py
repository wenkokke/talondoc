import sys

from docutils import nodes
from sphinx.util.typing import OptionSpec

from ...util.logging import getLogger
from ...util.nodes import colspec, entry, row, table, tbody, tgroup, title
from ...util.typing import optional_str, optional_strlist
from . import TalonCommandListDirective

_LOGGER = getLogger(__name__)


class TalonCommandTableDirective(TalonCommandListDirective):
    has_content = False
    required_arguments = 0
    optional_arguments = sys.maxsize
    option_spec: OptionSpec = {
        "package": optional_str,
        "caption": optional_str,
        "default": optional_str,
        "include": optional_strlist,
        "exclude": optional_strlist,
    }
    final_argument_whitespace = False

    def run(self) -> list[nodes.Node]:
        return [
            table(
                *[title(nodes.Text(caption)) for caption in self.caption()],
                tgroup(
                    colspec(colwidth=1),
                    colspec(colwidth=1),
                    tbody(
                        row(
                            entry(self.describe_rule(command)),
                            entry(
                                *self.describe_script(
                                    command,
                                    registry=self.talon.registry,
                                    include_script=False,
                                )
                            ),
                        )
                        for command in self.find_commands()
                    ),
                    cols=2,
                ),
                classes="compact",
            )
        ]
