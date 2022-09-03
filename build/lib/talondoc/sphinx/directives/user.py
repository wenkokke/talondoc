import os
import os.path
import platform

from docutils.nodes import Element

from .package import TalonPackageDirective


class TalonUserDirective(TalonPackageDirective):

    required_arguments = 0

    @property
    def talon_user(self) -> str:
        system = platform.system()
        if system == "Windows":
            return os.path.expandvars("%APPDATA%\\Talon\\user")
        else:
            return os.path.expanduser("~/.talon/user")

    def run(self) -> list[Element]:
        assert not hasattr(self, "arguments") or not self.arguments
        self.arguments: list[str] = [self.talon_user]
        return super().run()
