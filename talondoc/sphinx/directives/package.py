from pathlib import Path

from docutils.nodes import Element
from sphinx.util.typing import OptionSpec

from ...analyze import analyse_package
from ...analyze.registry import NoActiveFile, NoActivePackage, NoActiveRegistry
from ...util.logging import getLogger
from ...util.typing import optional_str, optional_strlist
from . import TalonDocDirective

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
                registry=self.talon.registry,
                package_dir=Path(self.arguments[0].strip()),
                package_name=self.options.get("name", "user"),
                include=tuple(self.options.get("include", ())),
                exclude=tuple(self.options.get("exclude", ())),
                trigger=tuple(self.options.get("trigger", ())),
            )
        except NoActiveRegistry as e:
            _logger.exception(e)
        except NoActivePackage as e:
            _logger.exception(e)
        except NoActiveFile as e:
            _logger.exception(e)

        return []