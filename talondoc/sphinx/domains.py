from typing import Optional
from sphinx.domains import Domain
from sphinx.util import logging
from .directives.package import TalonPackageDirective
from .directives.user import TalonUserDirective
from ..analyze.registry import Registry
from ..types import (
    ActionEntry,
    CommandEntry,
    FileEntry,
    ModuleEntry,
    ObjectEntry,
    PackageEntry,
    resolve_name,
)


class TalonDomain(Domain, Registry):
    """Talon language domain."""

    name = "talon"
    label = "Talon"

    directives = {
        "package": TalonPackageDirective,
        "user": TalonUserDirective,
    }

    @property
    def logger(self) -> logging.SphinxLoggerAdapter:
        return logging.getLogger(__name__)

    @property
    def actions(self) -> dict[str, ActionEntry]:
        return self.env.temp_data.setdefault(ActionEntry.sort, {})

    @property
    def commands(self) -> list[CommandEntry]:
        return self.env.temp_data.setdefault(CommandEntry.sort, [])

    @property
    def files(self) -> dict[str, FileEntry]:
        return self.env.temp_data.setdefault(FileEntry.sort, {})

    @property
    def modules(self) -> dict[str, list[ModuleEntry]]:
        return self.env.temp_data.setdefault(ModuleEntry.sort, {})

    @property
    def packages(self) -> dict[str, PackageEntry]:
        return self.env.temp_data.setdefault(PackageEntry.sort, {})

    _latest_file: Optional[FileEntry] = None

    def get_latest_file(self) -> Optional[FileEntry]:
        return self._latest_file

    def register(self, entry: ObjectEntry):
        if isinstance(entry, FileEntry):
            self._latest_file = entry
        self.logger.info(f"Register: {entry.qualified_name}")
        self.env.temp_data.setdefault(entry.sort, {})[entry.resolved_name] = entry

    def lookup(
        self, qualified_name: str, *, namespace: Optional[str] = None
    ) -> Optional[ObjectEntry]:
        sort, name = qualified_name.split(":", maxsplit=1)
        resolved_name = resolve_name(name, namespace=namespace)
        return self.env.temp_data.get(sort, {}).get(resolved_name, None)
