from functools import singledispatchmethod
from typing import Any, Optional
from sphinx.domains import Domain
from sphinx.util import logging
from .directives.package import TalonPackageDirective
from .directives.user import TalonUserDirective
from ..analyze.registry import NoActiveFile, Registry
from ..types import *


class TalonDomain(Domain, Registry):
    """Talon language domain."""

    name = "talon"
    label = "Talon"

    directives = {
        "package": TalonPackageDirective,
        "user": TalonUserDirective,
    }

    initial_data: dict[str, Any] = {
        "actions": {},
        "commands": [],
        "files": {},
        "modules": {},
        "packages": {},
    }

    @property
    def logger(self) -> logging.SphinxLoggerAdapter:
        return logging.getLogger(__name__)

    @property
    def actions(self) -> dict[str, ActionEntry]:
        return self.data.setdefault("actions", {})

    @property
    def commands(self) -> list[CommandEntry]:
        return self.data.setdefault("commands", [])

    @property
    def files(self) -> dict[str, FileEntry]:
        return self.data.setdefault("files", {})

    @property
    def modules(self) -> dict[str, list[ModuleEntry]]:
        return self.data.setdefault("modules", {})

    @property
    def packages(self) -> dict[str, PackageEntry]:
        return self.data.setdefault("packages", {})

    _latest_file: Optional[FileEntry] = None

    def get_latest_file(self) -> Optional[FileEntry]:
        return self._latest_file

    @singledispatchmethod
    def register(self, entry: ObjectEntry):
        raise TypeError(type(entry))

    @register.register
    def _(self, entry: PackageEntry):
        self.logger.info(f"Register: {entry.qualified_name}")
        self.packages[entry.qualified_name] = entry

    @register.register
    def _(self, entry: FileEntry):
        self._latest_file = entry
        self.logger.info(f"Register: {entry.qualified_name}")
        self.files[entry.qualified_name] = entry

    @register.register
    def _(self, entry: ModuleEntry):
        self.logger.info(f"Register: {entry.qualified_name}")
        self.modules.setdefault(entry.qualified_name, []).append(entry)

    @register.register
    def _(self, entry: ActionEntry):
        self.logger.info(f"Register: {entry.qualified_name}")
        self.actions[entry.qualified_name] = entry

    @register.register
    def _(self, entry: CommandEntry):
        self.logger.info(f"Register: {entry.qualified_name}")
        self.commands.append(entry)

    @singledispatchmethod
    def register_use(self, entry: ObjectEntry, entry_used: ObjectEntry):
        pass
