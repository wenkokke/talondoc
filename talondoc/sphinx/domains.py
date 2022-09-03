from typing import Optional, cast

from sphinx.domains import Domain

from talondoc.sphinx.directives.file import TalonFileDirective

from ..analyze.registry import Registry
from ..entries import (
    ActionEntry,
    ActionGroupEntry,
    CallbackEntry,
    CommandEntry,
    DuplicateAction,
    EventCode,
    FileEntry,
    ModuleEntry,
    ObjectEntry,
    PackageEntry,
    resolve_name,
)
from ..util.logging import getLogger
from .directives.command import TalonCommandDirective
from .directives.package import TalonPackageDirective
from .directives.user import TalonUserDirective

_logger = getLogger(__name__)


class TalonDomain(Domain, Registry):
    """Talon language domain."""

    name = "talon"
    label = "Talon"

    directives = {
        "command": TalonCommandDirective,
        "file": TalonFileDirective,
        "package": TalonPackageDirective,
        "user": TalonUserDirective,
    }

    @property
    def action_groups(self) -> dict[str, ActionGroupEntry]:
        return cast(
            dict[str, ActionGroupEntry],
            self.env.temp_data.setdefault(ActionGroupEntry.sort, {}),
        )

    @property
    def callbacks(self) -> dict[EventCode, list[CallbackEntry]]:
        return cast(
            dict[EventCode, list[CallbackEntry]],
            self.env.temp_data.setdefault(CallbackEntry.sort, {}),
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

    _currentpackage: Optional[PackageEntry] = None

    @property
    def currentpackage(self) -> Optional[PackageEntry]:
        return self._currentpackage

    _currentfile: Optional[FileEntry] = None

    @property
    def currentfile(self) -> Optional[FileEntry]:
        return self._currentfile

    def register(self, entry: ObjectEntry):
        # Track the current package:
        if isinstance(entry, PackageEntry):
            self._currentpackage = entry

        # Track the current file:
        if isinstance(entry, FileEntry):
            self._currentfile = entry

        # Store the entry:
        if isinstance(entry, ActionEntry):
            # Actions are stored as action groups:
            action_group_entry = self.action_groups.get(entry.name, None)
            if action_group_entry is None:
                self.action_groups[entry.name] = entry.group()
            else:
                try:
                    action_group_entry.append(entry)
                except DuplicateAction as e:
                    _logger.error(f"[talondoc] {e}")
        elif isinstance(entry, CallbackEntry):
            # Callbacks are stored as lists under their event codes:
            _logger.debug(
                f"[talondoc] Register '{entry.name}' for event '{entry.event_code}': {entry.file.name}"
            )
            self.callbacks.setdefault(entry.event_code, []).append(entry)
        elif isinstance(entry, CommandEntry):
            # Commands are stored as lists:
            self.commands.append(entry)
        else:
            # Everything else is stored under their resolved name:
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
