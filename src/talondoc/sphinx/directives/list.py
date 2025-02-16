from collections.abc import Mapping, Sequence

from docutils import nodes
from sphinx import addnodes
from typing_extensions import override

from ..._util.logging import getLogger
from ...analysis.registry import data
from ...analysis.registry.data.abc import UnknownReference
from .._util.addnodes import (
    NodeLike,
    colspec,
    desc_content,
    desc_literal,
    desc_qualname,
    desc_sig_operator,
    desc_sig_space,
    desc_type,
    entry,
    fragtable,
    paragraph,
    row,
    tbody,
    tgroup,
)
from . import TalonDocObjectDescription

_LOGGER = getLogger(__name__)


class TalonListDirective(TalonDocObjectDescription):
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
        default = self.talon.registry.lookup_default(data.List, sig)
        if default:
            desc_qualname(signode, default.name)

            # Add the type hint
            if default.value_type_hint:
                signode += desc_sig_operator(nodes.Text(":"))
                signode += desc_sig_space()
                signode += desc_type(default.value_type_hint)

            # Add the content
            content: list[NodeLike] = []

            # Add the description
            if default.description:
                content.append(paragraph(nodes.Text(default.description)))

            # Add the value
            if default.value:
                if isinstance(default.value, Mapping):
                    content.append(
                        fragtable(
                            tgroup(
                                colspec(colwidth=1),
                                colspec(colwidth=1),
                                tbody(
                                    row(
                                        entry(desc_literal(key)),
                                        entry(desc_literal(value)),
                                    )
                                    for key, value in default.value.items()
                                ),
                            ),
                        )
                    )
                elif isinstance(default.value, Sequence):
                    content.append(
                        fragtable(
                            tgroup(
                                colspec(colwidth=1),
                                tbody(
                                    row(
                                        entry(desc_literal(value)),
                                    )
                                    for value in default.value
                                ),
                            ),
                        )
                    )

            signode += desc_content(*content)

            return default.name
        e = UnknownReference(
            ref_type=data.List,
            ref_name=sig,
            location=self.get_location(),
            known_references=tuple(self.talon.registry.lists.keys()),
        )
        _LOGGER.error(f"talon:list: {e}")
        raise ValueError(e)
