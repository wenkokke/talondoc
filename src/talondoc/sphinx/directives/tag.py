from docutils import nodes
from sphinx import addnodes
from typing_extensions import override

from talondoc.analysis.registry.data.abc import UnknownReference

from ..._util.logging import getLogger
from ...analysis.registry import data
from .._util.addnodes import desc_content, desc_qualname, paragraph
from . import TalonDocObjectDescription

_LOGGER = getLogger(__name__)


class TalonTagDirective(TalonDocObjectDescription):
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False

    @override
    def get_signatures(self) -> list[str]:  # type: ignore[misc, name-defined]
        assert len(self.arguments) == 1
        return [str(self.arguments[0]).strip()]

    @override  # type: ignore[misc, name-defined]
    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        tag = self.talon.registry.lookup(data.Tag, sig)
        if tag:
            desc_qualname(signode, tag.name)
            if tag.description:
                signode += desc_content(paragraph(nodes.Text(tag.description)))
            return tag.name
        else:
            e = UnknownReference(
                ref_type=data.Tag,
                ref_name=sig,
                location=self.get_location(),
                known_references=tuple(self.talon.registry.tags.keys()),
            )
            _LOGGER.error(f"talon:tag: {e}")
            raise ValueError(e)
