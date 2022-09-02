from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from docutils.nodes import Element
from sphinx.directives import SphinxDirective
from sphinx.util.typing import OptionSpec

from ...analyze import analyse_package
from ...analyze.registry import Registry
from ...util.typing import optional_str, optional_strlist

if TYPE_CHECKING:
    from ..domains import TalonDomain
else:
    TalonDomain = Any


class TalonPackageDirective(SphinxDirective):

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    option_spec: OptionSpec = {
        "name": optional_str,
        "include": optional_strlist,
        "exclude": optional_strlist,
        "trigger": optional_strlist,
    }
    final_argument_whitespace = False

    @property
    def talon(self) -> TalonDomain:
        return cast(TalonDomain, self.env.get_domain("talon"))

    def run(self) -> list[Element]:

        # Always reread documents with Talon package directives.
        self.env.note_reread()

        # Analyse the referenced Talon package:
        analyse_package(
            registry=self.talon,
            package_root=Path(self.arguments[0].strip()),
            name=self.options.get("name"),
            include=tuple(self.options.get("include", ())),
            exclude=tuple(self.options.get("exclude", ())),
            trigger=tuple(self.options.get("trigger", ())),
        )

        return []
