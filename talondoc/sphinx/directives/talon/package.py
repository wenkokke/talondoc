import pathlib
from typing import NoReturn, cast
from docutils import nodes
from sphinx.directives import SphinxDirective
from ....analyze import Registry, analyse_package


class TalonPackageDirective(SphinxDirective):

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False

    def run(self) -> list[NoReturn]:
        analyse_package(
            registry=cast(Registry, self.env.get_domain("talon")),
            package_root=pathlib.Path(self.arguments[0].strip()),
        ),
        return []
