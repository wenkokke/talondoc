from sphinx.domains import Domain
from sphinx.environment import BuildEnvironment

from .._util.logging import getLogger
from ..analysis.registry import Registry
from .directives.action import TalonActionDirective
from .directives.capture import TalonCaptureDirective
from .directives.command import TalonCommandDirective
from .directives.command.table import TalonCommandTableDirective
from .directives.list import TalonListDirective
from .directives.mode import TalonModeDirective
from .directives.setting import TalonSettingDirective
from .directives.tag import TalonTagDirective

_LOGGER = getLogger(__name__)

__talonDirectiveClasses__ = TalonActionDirective | TalonCaptureDirective


class TalonDomain(Domain):  # type: ignore[misc]
    """Talon language domain."""

    name = "talon"
    label = "Talon"

    directives = {  # noqa: RUF012 (wants this to be a class var)
        "action": TalonActionDirective,
        "capture": TalonCaptureDirective,
        "command": TalonCommandDirective,
        "command-table": TalonCommandTableDirective,
        "list": TalonListDirective,
        "mode": TalonModeDirective,
        "setting": TalonSettingDirective,
        "tag": TalonTagDirective,
    }

    def __init__(self, env: BuildEnvironment):
        super().__init__(env)
        self.registry = Registry(
            data=self.data,
            temp_data=self.env.temp_data,
        )
        self.registry.load_builtin()

    @property
    def continue_on_error(self) -> bool:
        return bool(self.env.config["talon_continue_on_error"])
