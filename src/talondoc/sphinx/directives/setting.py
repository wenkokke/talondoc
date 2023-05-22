import inspect

from docutils import nodes
from sphinx import addnodes
from typing_extensions import final, override

from ..._util.logging import getLogger
from ...analysis.registry import data
from ...analysis.registry.data.abc import UnknownReference
from .._util.addnodes import (
    desc_content,
    desc_literal,
    desc_name,
    desc_qualname,
    desc_sig_element,
    desc_sig_literal_char,
    desc_sig_literal_number,
    desc_sig_literal_string,
    desc_sig_punctuation,
    desc_sig_space,
    desc_type,
    paragraph,
)
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
        default = self.talon.registry.lookup_default(data.Setting, sig)
        if default:
            # Add the setting name:
            desc_qualname(signode, default.name)

            # Add the setting type hint:
            if default.value_type_hint:
                signode += desc_sig_punctuation(nodes.Text(":"))
                signode += desc_sig_space()
                # TODO: This works for simple types, but should eventually
                #       be replaced with something more principled.
                signode += desc_type(default.value_type_hint)

            # Add the setting default value:
            if default.value:
                # TODO: This works for simple values, but should eventually
                #       be replaced with something more principled.
                signode += desc_sig_space()
                signode += desc_sig_punctuation(nodes.Text("="))
                signode += desc_sig_space()
                signode += desc_literal(default.value)

            # Add the setting description:
            if default.description:
                signode += desc_content(paragraph(nodes.Text(default.description)))

            return default.name
        else:
            e = UnknownReference(
                ref_type=data.Setting,
                ref_name=sig,
                location=self.get_location(),
                known_references=tuple(self.talon.registry.settings.keys()),
            )
            _LOGGER.error(e)
            raise ValueError(e)
