from docutils import nodes
from sphinx import addnodes
from typing_extensions import override

from ..._util.logging import getLogger
from ...analysis.registry import data
from ...analysis.registry.data.abc import UnknownReference
from .._util.addnodes import desc_content, desc_qualname, paragraph
from . import TalonDocObjectDescription

_LOGGER = getLogger(__name__)


class TalonModeDirective(TalonDocObjectDescription):
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False

    @override  # type: ignore[misc]
    def get_signatures(self) -> list[str]:
        if not len(self.arguments) == 1:
            raise ValueError("invalid signature")
        return [str(self.arguments[0]).strip()]

    @override  # type: ignore[misc]
    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        mode = self.talon.registry.lookup(data.Mode, sig)
        if mode:
            desc_qualname(signode, mode.name)
            if mode.description:
                signode += desc_content(paragraph(nodes.Text(mode.description)))
            return mode.name
        e = UnknownReference(
            ref_type=data.Mode,
            ref_name=sig,
            location=self.get_location(),
            known_references=tuple(self.talon.registry.modes.keys()),
        )
        _LOGGER.error(f"talon:mode: {e}")
        raise ValueError(e)
