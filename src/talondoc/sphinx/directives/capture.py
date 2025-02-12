from inspect import Signature

from docutils import nodes
from sphinx import addnodes
from typing_extensions import override

from ..._util.logging import getLogger
from ...analysis.registry import data
from ...analysis.registry.data.abc import UnknownReference
from .._util.addnodes import (
    desc_content,
    desc_qualname,
    desc_sig_operator,
    desc_sig_space,
    desc_type,
    paragraph,
)
from .._util.addnodes.rule import desc_rule
from . import TalonDocObjectDescription

_LOGGER = getLogger(__name__)


class TalonCaptureDirective(TalonDocObjectDescription):
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
        default = self.talon.registry.lookup_default(data.Capture, sig)
        if default:
            desc_qualname(signode, default.name)

            # Add the return type
            if (
                default.function_signature
                and default.function_signature.return_annotation is not Signature.empty
            ):
                signode += desc_sig_operator(nodes.Text(":"))
                signode += desc_sig_space()
                signode += desc_type(default.function_signature.return_annotation)

            # Add the rule
            signode += desc_content(desc_rule(default.rule))

            # Add the description
            if default.description:
                signode += desc_content(paragraph(nodes.Text(default.description)))

            return default.name
        e = UnknownReference(
            ref_type=data.Capture,
            ref_name=sig,
            location=self.get_location(),
            known_references=tuple(self.talon.registry.captures.keys()),
        )
        _LOGGER.error(f"talon:capture: {e}")
        raise ValueError(e)
