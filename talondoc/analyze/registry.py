import abc
import itertools
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional, Union, cast, overload

from ..util.logging import getLogger
from .entries import (
    ActionEntry,
    AnyFileEntry,
    AnyModuleEntry,
    CallbackEntry,
    CanOverride,
    CanOverrideEntry,
    CaptureEntry,
    CommandEntry,
    ContextEntry,
    DuplicateEntry,
    Entry,
    EventCode,
    FileEntry,
    FunctionEntry,
    GroupEntry,
    ListEntry,
    ModeEntry,
    ModuleEntry,
    ObjectEntry,
    PackageEntry,
    SettingEntry,
    TagEntry,
    resolve_name,
)

_LOGGER = getLogger(__name__)


class NoActiveRegistry(Exception):
    """
    Exception raised when the user attempts to load a talon module
    outside of the 'talon_shims' context manager.
    """

    def __str__(self) -> str:
        return "No active registry"


class NoActivePackage(Exception):
    """
    Exception raised when the user attempts to get the active package
    when no package has been processed.
    """

    def __str__(self) -> str:
        return "No active package"


class NoActiveFile(Exception):
    """
    Exception raised when the user attempts to get the active file
    when no file has been processed.
    """

    def __str__(self) -> str:
        return "No active file"


@dataclass
class Registry:

    data: dict[str, Any] = field(default_factory=dict)

    temp_data: dict[str, Any] = field(default_factory=dict)

    _active_package_entry: Optional[PackageEntry] = field(default=None, init=False)

    _active_file_entry: Optional[FileEntry] = field(default=None, init=False)

    @property
    def active_package_entry(self) -> Optional[PackageEntry]:
        return self._active_package_entry

    @active_package_entry.setter
    def active_package_entry(self, package_entry: PackageEntry) -> None:
        self._active_package_entry = package_entry

    @property
    def active_file_entry(self) -> Optional[FileEntry]:
        return self._active_file_entry

    @active_file_entry.setter
    def active_file_entry(self, file_entry: FileEntry) -> None:
        self._active_file_entry = file_entry

    @property
    def groups(self) -> dict[str, dict[str, GroupEntry]]:
        return cast(
            dict[str, dict[str, GroupEntry]],
            self.data.setdefault(GroupEntry.sort, {}),
        )

    @property
    def action_groups(self) -> dict[str, GroupEntry[ActionEntry]]:
        return cast(
            dict[str, GroupEntry[ActionEntry]],
            self.groups.setdefault(ActionEntry.sort, {}),
        )

    @property
    def capture_groups(self) -> dict[str, GroupEntry[CaptureEntry]]:
        return cast(
            dict[str, GroupEntry[CaptureEntry]],
            self.groups.setdefault(CaptureEntry.sort, {}),
        )

    @property
    def list_groups(self) -> dict[str, GroupEntry[ListEntry]]:
        return cast(
            dict[str, GroupEntry[ListEntry]],
            self.groups.setdefault(ListEntry.sort, {}),
        )

    @property
    def setting_groups(self) -> dict[str, GroupEntry[SettingEntry]]:
        return cast(
            dict[str, GroupEntry[SettingEntry]],
            self.groups.setdefault(SettingEntry.sort, {}),
        )

    @property
    def callbacks(self) -> dict[EventCode, list[CallbackEntry]]:
        return cast(
            dict[EventCode, list[CallbackEntry]],
            self.temp_data.setdefault(CallbackEntry.sort, {}),
        )

    @property
    def commands(self) -> list[CommandEntry]:
        return cast(
            list[CommandEntry],
            self.data.setdefault(CommandEntry.sort, []),
        )

    @property
    def contexts(self) -> dict[str, list[ContextEntry]]:
        return cast(
            dict[str, list[ContextEntry]],
            self.data.setdefault(ContextEntry.sort, {}),
        )

    @property
    def files(self) -> dict[str, FileEntry]:
        return cast(
            dict[str, FileEntry],
            self.data.setdefault(FileEntry.sort, {}),
        )

    @property
    def functions(self) -> dict[str, FunctionEntry]:
        return cast(
            dict[str, FunctionEntry],
            self.temp_data.setdefault(FunctionEntry.sort, {}),
        )

    @property
    def modes(self) -> dict[str, ModeEntry]:
        return cast(
            dict[str, ModeEntry],
            self.data.setdefault(ModeEntry.sort, {}),
        )

    @property
    def modules(self) -> dict[str, list[ModuleEntry]]:
        return cast(
            dict[str, list[ModuleEntry]],
            self.data.setdefault(ModuleEntry.sort, {}),
        )

    @property
    def packages(self) -> dict[str, PackageEntry]:
        return cast(
            dict[str, PackageEntry],
            self.data.setdefault(PackageEntry.sort, {}),
        )

    @property
    def tags(self) -> dict[str, TagEntry]:
        return cast(
            dict[str, TagEntry],
            self.data.setdefault(TagEntry.sort, {}),
        )

    def register(self, entry: ObjectEntry):
        """
        Register an object entry.
        """
        # Track the current package:
        if isinstance(entry, PackageEntry):
            self._active_package_entry = entry

        # Track the current file:
        if isinstance(entry, FileEntry):
            self._active_file_entry = entry

        # Store the entry:
        if isinstance(entry, FunctionEntry):
            # Functions are TEMPORARY DATA, and are stored under their qualified names:
            if entry.resolved_name in self.functions:
                e = DuplicateEntry(entry, self.functions[entry.resolved_name])
                _LOGGER.exception(e)
            else:
                self.functions[entry.resolved_name] = entry
        elif isinstance(entry, CallbackEntry):
            # Callbacks are TEMPORARY DATA, and are stored as lists under their event codes:
            self.callbacks.setdefault(entry.event_code, []).append(entry)
        elif isinstance(entry, CanOverrideEntry):
            # Objects that can be overwritten are stored as groups:
            object_groups = self.groups.setdefault(entry.__class__.sort, {})
            object_group = object_groups.get(entry.resolved_name, None)
            if object_group:
                try:
                    object_group.append(entry)
                except DuplicateEntry as e:
                    _LOGGER.exception(e)
            else:
                object_groups[entry.resolved_name] = entry.group()
        elif isinstance(entry, CommandEntry):
            # Commands are stored as lists:
            self.commands.append(entry)
        else:
            # Everything else is stored under its resolved name:
            self.data.setdefault(entry.sort, {})[entry.resolved_name] = entry

    @overload
    def lookup(
        self, sort: type[PackageEntry], name: str, *, namespace: Optional[str] = None
    ) -> Optional[PackageEntry]:
        ...

    @overload
    def lookup(
        self, sort: type[FunctionEntry], name: str, *, namespace: Optional[str] = None
    ) -> Optional[FunctionEntry]:
        ...

    @overload
    def lookup(
        self, sort: type[CallbackEntry], name: str, *, namespace: Optional[str] = None
    ) -> Optional[Sequence[CallbackEntry]]:
        ...

    @overload
    def lookup(
        self, sort: type[AnyFileEntry], name: str, *, namespace: Optional[str] = None
    ) -> Optional[AnyFileEntry]:
        ...

    @overload
    def lookup(
        self, sort: type[CommandEntry], name: str, *, namespace: Optional[str] = None
    ) -> Optional[Sequence[CommandEntry]]:
        ...

    @overload
    def lookup(
        self, sort: type[AnyModuleEntry], name: str, *, namespace: Optional[str] = None
    ) -> Optional[AnyModuleEntry]:
        ...

    @overload
    def lookup(
        self, sort: type[CanOverride], name: str, *, namespace: Optional[str] = None
    ) -> Optional[GroupEntry[CanOverride]]:
        ...

    @overload
    def lookup(
        self, sort: type[ModeEntry], name: str, *, namespace: Optional[str] = None
    ) -> Optional[ModeEntry]:
        ...

    @overload
    def lookup(
        self, sort: type[TagEntry], name: str, *, namespace: Optional[str] = None
    ) -> Optional[TagEntry]:
        ...

    def lookup(
        self, sort: type[Entry], name: str, *, namespace: Optional[str] = None
    ) -> Union[None, Entry, GroupEntry, Sequence[Entry]]:
        """
        Look up an object entry by its name.
        """
        if issubclass(sort, CanOverrideEntry):
            return cast(
                Optional[GroupEntry[Entry]],  # type: ignore
                self.groups.get(sort.sort, {}).get(name, None),
            )
        else:
            return cast(
                Optional[Union[Entry, Sequence[Entry]]],
                self.data.get(sort.sort, {}).get(name, None),
            )

    ##################################################
    # The active GLOBAL registry
    ##################################################

    _active_global_registry: ClassVar[Optional["Registry"]]

    @staticmethod
    def get_active_global_registry() -> "Registry":
        if Registry._active_global_registry:
            return Registry._active_global_registry
        else:
            raise NoActiveRegistry()

    @staticmethod
    def get_active_package() -> PackageEntry:
        """
        Retrieve the active package.
        """
        registry = Registry.get_active_global_registry()
        if registry.active_package_entry:
            return registry.active_package_entry
        else:
            raise NoActivePackage()

    @staticmethod
    def set_active_package(package_entry: PackageEntry) -> None:
        """
        Set the active package.
        """
        registry = Registry.get_active_global_registry()
        registry.active_package_entry = package_entry

    @staticmethod
    def get_active_file() -> FileEntry:
        """
        Retrieve the active file.
        """
        registry = Registry.get_active_global_registry()
        if registry.active_file_entry:
            return registry.active_file_entry
        else:
            raise NoActiveFile()

    @staticmethod
    def set_active_file(file_entry: FileEntry) -> None:
        """
        Set the active file.
        """
        registry = Registry.get_active_global_registry()
        registry.active_file_entry = file_entry

    def activate(self: Optional["Registry"]):
        """
        Set this registry as the current active registry.
        """
        Registry._active_global_registry = self
