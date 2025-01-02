import inspect

from docutils import nodes
from sphinx import addnodes
from typing_extensions import override

from ..._util.logging import getLogger
from ...analysis.registry import data
from ...analysis.registry.data.abc import UnknownReference
from .._util.addnodes import desc_content, desc_qualname, desc_signature, paragraph
from . import TalonDocObjectDescription

_LOGGER = getLogger(__name__)


class TalonActionDirective(TalonDocObjectDescription):
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False

    @override  # type: ignore[misc]
    def get_signatures(self) -> list[str]:
        assert len(self.arguments) == 1
        return [str(self.arguments[0]).strip()]

    @override  # type: ignore[misc]
    def handle_signature(self, sig: str, signode: addnodes.desc_signature) -> str:
        default = self.talon.registry.lookup_default(data.Action, sig)
        if default:
            # Add the action name:
            desc_qualname(signode, default.name)

            # Add the action type signature:
            desc_signature(signode, default.function_signature or inspect.Signature())

            if default.description:
                signode += desc_content(paragraph(nodes.Text(default.description)))
            return default.name
        else:
            e = UnknownReference(
                ref_type=data.Action,
                ref_name=sig,
                location=self.get_location(),
                known_references=tuple(self.talon.registry.actions.keys()),
            )
            _LOGGER.error(f"talon:action: {e}")
            raise ValueError(e)
