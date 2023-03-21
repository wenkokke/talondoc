import sys

from docutils import nodes
from sphinx.util.typing import OptionSpec

from ....util.nodes import colspec, entry, row, table, tbody, tgroup, title
from ....util.typing import optional_str, optional_strlist
from .util import TalonCommandListDirective, describe_rule, describe_script


class TalonCommandTableDirective(TalonCommandListDirective):
    has_content = False
    required_arguments = 0
    optional_arguments = sys.maxsize
    option_spec: OptionSpec = {
        "package": optional_strlist,
        "context": optional_strlist,
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
                            entry(describe_rule(command)),
                            entry(
                                *describe_script(
                                    command,
                                    registry=self.talon.registry,
                                    include_script=False,
                                    docstring_hook=self.docstring_hook,
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
