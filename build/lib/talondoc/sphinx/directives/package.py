from pathlib import Path
from typing import Optional, cast

from docutils.nodes import Element
from sphinx.directives import SphinxDirective
from sphinx.util.typing import OptionSpec

from ...analyze import Registry, analyse_package
from ...analyze.registry import Registry
from ...util.typing import optional_str, optional_strlist


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

    def run(self) -> list[Element]:

        # Always reread documents with Talon package directives.
        self.env.note_reread()

        # Analyse the referenced Talon package.
        name: Optional[str] = self.options.get("name")
        include: tuple[str, ...] = self.options.get("include", ())
        exclude: tuple[str, ...] = self.options.get("exclude", ())
        registry = cast(Registry, self.env.get_domain("talon"))

        analyse_package(
            registry=registry,
            package_root=Path(self.arguments[0].strip()),
            name=name,
            include=tuple(include),
            exclude=tuple(exclude),
        ),

        # TODO: register & trigger callbacks

        return []
