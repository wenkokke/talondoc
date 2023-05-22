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
    if "width" in node:
        width = cast(Optional[int], node["width"])
        if width:
            atts["style"] = (
                f"column-width: {width}px;" f"column-fill: balance;" f"width: 100%;"
            )
    tag = self.starttag(node, "div", **atts)
    self.body.append(tag)
    self.visit_table(node)


def depart_fragtable_html(self: HTML5Translator, node: fragtable) -> None:
    self.depart_table(node)
    self.body.append("</div>\n")


def visit_fragtable(self: SphinxTranslator, node: fragtable) -> None:
    self.visit_table(node)


def depart_fragtable(self: SphinxTranslator, node: fragtable) -> None:
    self.depart_table(node)
