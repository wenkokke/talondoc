import sys
from typing import Optional

from docutils import nodes
from sphinx.util.typing import OptionSpec

from ...util.addnodes import colspec, entry, row, table, tbody, tgroup, title
from ...util.typing import flag, optional_str, optional_strlist
from .abc import TalonDocCommandDescription


class TalonCommandTableDirective(TalonDocCommandDescription):
    has_content = False
    required_arguments = 0
    optional_arguments = sys.maxsize
    option_spec: OptionSpec = {
        "restrict_to": optional_strlist,
        "always_include_script": flag,
        "caption": optional_str,
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

    def run(self) -> list[nodes.Node]:
        return [
            table(
                *[title(nodes.Text(caption)) for caption in self.caption],
                tgroup(
                    colspec(colwidth=1),
                    colspec(colwidth=1),
                    tbody(
                        row(
                            entry(self.describe_rule(command.rule)),
                            entry(
                                *self.describe_script(
                                    command,
                                    always_include_script=self.always_include_script,
                                    docstring_hook=self.docstring_hook,
                                )
                            ),
                        )
                        for command in self.get_commands(restrict_to=self.restrict_to)
                    ),
                    cols=2,
                ),
                classes="compact",
            )
        ]
