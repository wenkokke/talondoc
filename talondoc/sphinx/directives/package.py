from pathlib import Path

from docutils.nodes import Element
from sphinx.util.typing import OptionSpec
from ...analyze.registry import NoActiveFile, NoActivePackage, NoActiveRegistry

from ...analyze import analyse_package
from ...util.typing import optional_str, optional_strlist
from .core import TalonDocDirective
from ...util.logging import getLogger

_logger = getLogger(__name__)


class TalonPackageDirective(TalonDocDirective):

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

        # Analyse the referenced Talon package:
        try:
            analyse_package(
                registry=self.talon,
                package_root=Path(self.arguments[0].strip()),
                name=self.options.get("name", "user"),
                include=tuple(self.options.get("include", ())),
                exclude=tuple(self.options.get("exclude", ())),
                trigger=tuple(self.options.get("trigger", ())),
            )
        except (NoActiveRegistry, NoActivePackage, NoActiveFile) as e:
            _logger.exception(e)

        return []
