from docutils import nodes
from sphinx import addnodes
from typing_extensions import override

from ..._util.logging import getLogger
from ...analysis.registry import data
from ...analysis.registry.data.abc import UnknownReference
from .._util.addnodes import desc_content, desc_name, paragraph
from . import TalonDocObjectDescription

_LOGGER = getLogger(__name__)


class TalonSettingDirective(TalonDocObjectDescription):
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False

    @override
    def get_signatures(self) -> list[str]:
        assert len(self.arguments) == 1
        return [str(self.arguments[0]).strip()]

    @override
    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        (
            declaration,
            default_overrides,
            other_overrides,
        ) = self.talon.registry.lookup_partition(data.Setting, sig)
        if declaration:
            signode += desc_name(nodes.Text(declaration.name))
            if declaration.description:
                signode += desc_content(paragraph(nodes.Text(declaration.description)))
            return declaration.name
        else:
            e = UnknownReference(
                ref_type=data.Setting,
                ref_name=sig,
                location=self.get_location(),
                known_references=tuple(self.talon.registry.settings.keys()),
            )
            _LOGGER.error(e)
            raise ValueError(e)
