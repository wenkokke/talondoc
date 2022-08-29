import os
import os.path
import platform
import typing

from docutils import nodes
from .package import TalonPackageDirective


class TalonUserDirective(TalonPackageDirective):

    has_content = False
    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False

    @property
    def talon_user(self) -> str:
        system = platform.system()
        if system == "Windows":
            return os.path.expandvars("%APPDATA%\\Talon\\user")
        else:
            return os.path.expanduser("~/.talon/user")

    def run(self) -> list[nodes.Element]:
        assert not hasattr(self, 'arguments') or not self.arguments
        self.arguments: list[str] = [self.talon_user]
        return super().run()
