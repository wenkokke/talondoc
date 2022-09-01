from typing import Optional, cast

from sphinx.domains import Domain
from sphinx.util import logging

from ..analyze.registry import Registry
from ..types import (
    ActionGroupEntry,
    CommandEntry,
    FileEntry,
    ModuleEntry,
    ObjectEntry,
    PackageEntry,
    resolve_name,
)
from .directives.package import TalonPackageDirective
from .directives.user import TalonUserDirective
from .directives.command import TalonCommandDirective


class TalonDomain(Domain, Registry):
    """Talon language domain."""

    name = "talon"
    label = "Talon"

    directives = {
        "command": TalonCommandDirective,
        "package": TalonPackageDirective,
        "user": TalonUserDirective,
    }

    @property
    def logger(self) -> logging.SphinxLoggerAdapter:
        return logging.getLogger(__name__)

    @property
    def action_groups(self) -> dict[str, ActionGroupEntry]:
        return cast(
            dict[str, ActionGroupEntry],
            self.env.temp_data.setdefault(ActionGroupEntry.sort, {}),
        )

    @property
    def commands(self) -> list[CommandEntry]:
        return cast(
            list[CommandEntry],
            self.env.temp_data.setdefault(CommandEntry.sort, []),
        )

    @property
    def files(self) -> dict[str, FileEntry]:
        return cast(
            dict[str, FileEntry],
            self.env.temp_data.setdefault(FileEntry.sort, {}),
        )

    @property
    def modules(self) -> dict[str, list[ModuleEntry]]:
        return cast(
            dict[str, list[ModuleEntry]],
            self.env.temp_data.setdefault(ModuleEntry.sort, {}),
        )

    @property
    def packages(self) -> dict[str, PackageEntry]:
        return cast(
            dict[str, PackageEntry],
            self.env.temp_data.setdefault(PackageEntry.sort, {}),
        )

    _currentfile: Optional[FileEntry] = None

    def get_latest_file(self) -> Optional[FileEntry]:
        return self._currentfile

    def register(self, entry: ObjectEntry):
        if isinstance(entry, FileEntry):
            self._currentfile = entry
        if isinstance(entry, CommandEntry):
            self.commands.append(entry)
        else:
            self.env.temp_data.setdefault(entry.sort, {})[entry.resolved_name] = entry

    def lookup(
        self, qualified_name: str, *, namespace: Optional[str] = None
    ) -> Optional[ObjectEntry]:
        sort, name = qualified_name.split(":", maxsplit=1)
        resolved_name = resolve_name(name, namespace=namespace)
        return cast(
            Optional[ObjectEntry],
            self.env.temp_data.get(sort, {}).get(resolved_name, None),
        )
