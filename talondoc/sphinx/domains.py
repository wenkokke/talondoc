from sphinx.domains import Domain
from sphinx.environment import BuildEnvironment

from ..registry import Registry
from ..sphinx.directives.command.hlist import TalonCommandHListDirective
from ..sphinx.directives.command.table import TalonCommandTableDirective
from ..util.logging import getLogger
from .directives.command import TalonCommandDirective
from .directives.package import TalonPackageDirective
from .directives.user import TalonUserDirective

_LOGGER = getLogger(__name__)


class TalonDomain(Domain):
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

    def __init__(self, env: BuildEnvironment):
        super().__init__(env)
        self.registry = Registry(
            data=self.data,
            temp_data=self.env.temp_data,
        )
