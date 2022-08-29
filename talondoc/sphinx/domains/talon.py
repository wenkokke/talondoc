from functools import singledispatchmethod
from typing import Any
from sphinx.domains import Domain
from sphinx.util import logging
from ..directives.talon.package import TalonPackageDirective
from ..directives.talon.user import TalonUserDirective
from ...analyze import Registry
from ...types import *


class TalonDomain(Domain, Registry):
    """Talon language domain."""

    name = "talon"
    label = "Talon"

    directives = {
        "package": TalonPackageDirective,
        "user": TalonUserDirective,
    }

    initial_data: dict[str, Any] = {
        "packages": {},
        "files": {},
        "commands": [],
    }

    @property
    def logger(self) -> logging.SphinxLoggerAdapter:
        return logging.getLogger(__name__)

    @property
    def packages(self) -> dict[str, PackageEntry]:
        return self.data.setdefault("packages", {})

    @property
    def files(self) -> dict[str, FileEntry]:
        return self.data.setdefault("files", {})

    @property
    def commands(self) -> list[CommandEntry]:
        return self.data.setdefault("commands", [])

    @singledispatchmethod
    def register_entry(self, entry: ObjectEntry):
        raise TypeError(type(entry))

    @register_entry.register
    def _(self, entry: PackageEntry):
        self.logger.info(f"Register: {entry.qualified_name}")
        self.packages[entry.qualified_name] = entry

    @register_entry.register
    def _(self, entry: FileEntry):
        self.logger.info(f"Register: {entry.qualified_name}")
        self.files[entry.qualified_name] = entry

    @register_entry.register
    def _(self, entry: CommandEntry):
        self.logger.info(f"Register: {entry.qualified_name}")
        self.commands.append(entry)

    @singledispatchmethod
    def register_use(self, entry: ObjectEntry, entry_used: ObjectEntry):
        pass