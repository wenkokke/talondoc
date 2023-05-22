from docutils import nodes
from sphinx.locale import _
from talonfmt import talonfmt

from ...._util.logging import getLogger
from ....analysis.registry import data

_LOGGER = getLogger(__name__)


def desc_rule(rule: data.Rule) -> nodes.Text:
    return nodes.Text(talonfmt(rule, safe=False))
