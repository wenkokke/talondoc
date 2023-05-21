from sphinx.domains import Domain
from sphinx.environment import BuildEnvironment

from .._util.logging import getLogger
from ..analysis.registry import Registry
from .directives.capture import TalonCaptureDirective
from .directives.command import TalonCommandDirective
from .directives.command.hlist import TalonCommandHListDirective
from .directives.command.table import TalonCommandTableDirective
from .directives.list import TalonListDirective
from .directives.mode import TalonModeDirective
from .directives.tag import TalonTagDirective

_LOGGER = getLogger(__name__)


class TalonDomain(Domain):  # type: ignore[misc]
    """Talon language domain."""

    name = "talon"
    label = "Talon"

    directives = {
        "capture": TalonCaptureDirective,
        "command": TalonCommandDirective,
        "command-hlist": TalonCommandHListDirective,
        "command-table": TalonCommandTableDirective,
        "list": TalonListDirective,
        "mode": TalonModeDirective,
        "tag": TalonTagDirective,
    }

    def __init__(self, env: BuildEnvironment):
        super().__init__(env)
        self.registry = Registry(
            data=self.data,
            temp_data=self.env.temp_data,
        )
        self.registry.load_builtin()
