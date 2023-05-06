from sphinx.domains import Domain
from sphinx.environment import BuildEnvironment

from ..registry import Registry
from ..util.logging import getLogger
from .directives.command import TalonCommandDirective
from .directives.command.hlist import TalonCommandHListDirective
from .directives.command.table import TalonCommandTableDirective

_LOGGER = getLogger(__name__)


class TalonDomain(Domain):
    """Talon language domain."""

    name = "talon"
    label = "Talon"

    directives = {
        "command": TalonCommandDirective,
        "command-hlist": TalonCommandHListDirective,
        "command-table": TalonCommandTableDirective,
    }

    def __init__(self, env: BuildEnvironment):
        super().__init__(env)
        self.registry = Registry(
            data=self.env.temp_data,
            temp_data=self.env.temp_data,
        )
