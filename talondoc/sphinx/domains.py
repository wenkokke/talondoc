from typing import Any

from sphinx.domains import Domain

from talondoc.sphinx.directives.command_hlist import TalonCommandHListDirective
from talondoc.sphinx.directives.command_table import TalonCommandTableDirective

from ..analyze.registry import Registry
from ..util.logging import getLogger
from .directives.command import TalonCommandDirective
from .directives.package import TalonPackageDirective
from .directives.user import TalonUserDirective

_logger = getLogger(__name__)


class TalonDomain(Domain, Registry):
    """Talon language domain."""

    name = "talon"
    label = "Talon"

    directives = {
        "command": TalonCommandDirective,
        "command-hlist": TalonCommandHListDirective,
        "command-table": TalonCommandTableDirective,
        "package": TalonPackageDirective,
        "user": TalonUserDirective,
    }

    @property
    def registry(self) -> dict[str, Any]:
        return self.env.temp_data
