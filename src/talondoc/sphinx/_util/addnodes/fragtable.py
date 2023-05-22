from typing import Any, Optional, cast

from docutils import nodes
from sphinx.locale import _
from sphinx.util.docutils import SphinxTranslator
from sphinx.writers.html5 import HTML5Translator

from ...._util.logging import getLogger

_LOGGER = getLogger(__name__)

################################################################################
# Fragmenting Table
################################################################################


class fragtable(nodes.table):  # type: ignore[misc]
    pass


def visit_fragtable_html(self: HTML5Translator, node: fragtable) -> None:
    atts: dict[str, Any] = {"classes": ["fragtable"]}
    if "table_width" in node:
        table_width = cast(Optional[int], node["table_width"])
        if table_width:
            atts["style"] = (
                f"column-width: {table_width}px;"
                f"column-fill: balance;"
                f"width: 100%;"
            )
    tag = self.starttag(node, "div", **atts)
    self.body.append(tag)
    self.visit_table(node)


def depart_fragtable_html(self: HTML5Translator, node: fragtable) -> None:
    self.body.append("</div>\n")
    self.depart_table(node)


def visit_fragtable(self: SphinxTranslator, node: fragtable) -> None:
    self.visit_table(node)


def depart_fragtable(self: SphinxTranslator, node: fragtable) -> None:
    self.depart_table(node)
