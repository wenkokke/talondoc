from docutils import nodes
from sphinx import addnodes
from typing_extensions import override

from ..._util.logging import getLogger
from ...analysis.registry import data
from .._util.addnodes import desc_content, desc_name, paragraph
from . import TalonDocObjectDescription
from .errors import UnmatchedSignature

_LOGGER = getLogger(__name__)


class TalonCaptureDirective(TalonDocObjectDescription):
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False

    @override
    def get_signatures(self) -> list[str]:
        assert len(self.arguments) == 1
        return [str(self.arguments[0])]

    @override
    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        (
            declaration,
            default_overrides,
            other_overrides,
        ) = self.talon.registry.lookup_partition(data.Capture, sig)
        if declaration:
            signode += desc_name(nodes.Text(declaration.name))
            signode += desc_content(self.describe_rule(declaration.rule))
            if declaration.description:
                signode += desc_content(paragraph(nodes.Text(declaration.description)))
            return declaration.name
        raise UnmatchedSignature(self.get_location(), sig)
