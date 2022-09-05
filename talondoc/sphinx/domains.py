from sphinx.domains import Domain
from sphinx.environment import BuildEnvironment

from ..analyze.registry import Registry, StandaloneRegistry
from ..sphinx.directives.command_hlist import TalonCommandHListDirective
from ..sphinx.directives.command_table import TalonCommandTableDirective
from ..util.logging import getLogger
from .directives.command import TalonCommandDirective
from .directives.package import TalonPackageDirective
from .directives.user import TalonUserDirective

_logger = getLogger(__name__)


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
        self.registry: Registry = StandaloneRegistry(
            data=self.data,
            temp_data=self.env.temp_data,
        )
