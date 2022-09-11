import abc
from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional, cast

from ..util.logging import getLogger
from .entries import (
    ActionEntry,
    ActionGroupEntry,
    CallbackEntry,
    CaptureEntry,
    CommandEntry,
    ContextEntry,
    DuplicateEntry,
    EventCode,
    FileEntry,
    FunctionEntry,
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


class Registry(abc.ABC):

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
        if registry.latest_package:
            return registry.latest_package
        else:
            raise NoActivePackage()

    @staticmethod
    def get_active_file() -> FileEntry:
        """
        Retrieve the active file.
        """
        registry = Registry.get_active_global_registry()
        if registry.latest_file:
            return registry.latest_file
        else:
            raise NoActiveFile()

    def activate(self: Optional["Registry"]):
        """
        Set this registry as the current active registry.
        """
        Registry._active_global_registry = self

    ##################################################
    # The API for any particular registry
    ##################################################

    @abc.abstractproperty
    def latest_package(self) -> Optional[PackageEntry]:
        """
        Get the most recently registered package.
        """

    @abc.abstractproperty
    def latest_file(self) -> Optional[FileEntry]:
        """
        Get the most recently registered file.
        """

    @abc.abstractproperty
    def action_groups(self) -> dict[str, ActionGroupEntry]:
        pass

    @abc.abstractproperty
    def callbacks(self) -> dict[EventCode, list[CallbackEntry]]:
        pass

    @abc.abstractproperty
    def captures(self) -> dict[str, CaptureEntry]:
        pass

    @abc.abstractproperty
    def commands(self) -> list[CommandEntry]:
        pass

    @abc.abstractproperty
    def contexts(self) -> dict[str, list[ContextEntry]]:
        pass

    @abc.abstractproperty
    def files(self) -> dict[str, FileEntry]:
        pass

    @abc.abstractproperty
    def modes(self) -> dict[str, ModeEntry]:
        pass

    @abc.abstractproperty
    def modules(self) -> dict[str, list[ModuleEntry]]:
        pass

    @abc.abstractproperty
    def lists(self) -> dict[str, ListEntry]:
        pass

    @abc.abstractproperty
    def packages(self) -> dict[str, PackageEntry]:
        pass

    @abc.abstractproperty
    def settings(self) -> dict[str, SettingEntry]:
        pass

    @abc.abstractproperty
    def tags(self) -> dict[str, TagEntry]:
        pass

    @abc.abstractmethod
    def register(self, entry: ObjectEntry):
        """
        Register an object entry.
        """

    @abc.abstractmethod
    def lookup(
        self, qualified_name: str, *, namespace: Optional[str] = None
    ) -> Optional[ObjectEntry]:
        """
        Look up an object entry by its qualifiedd name.
        """


@dataclass
class StandaloneRegistry(Registry):

    data: dict[str, Any] = field(default_factory=dict)

    temp_data: dict[str, Any] = field(default_factory=dict)

    _latest_package: Optional[PackageEntry] = field(default=None, init=False)

    _latest_file: Optional[FileEntry] = field(default=None, init=False)

    @property
    def latest_package(self) -> Optional[PackageEntry]:
        """
        Get the most recently registered package.
        """
        return self._latest_package

    @property
    def latest_file(self) -> Optional[FileEntry]:
        """
        Get the most recently registered file.
        """
        return self._latest_file

    @property
    def action_groups(self) -> dict[str, ActionGroupEntry]:
        return cast(
            dict[str, ActionGroupEntry],
            self.data.setdefault(ActionGroupEntry.sort, {}),
        )

    @property
    def callbacks(self) -> dict[EventCode, list[CallbackEntry]]:
        return cast(
            dict[EventCode, list[CallbackEntry]],
            self.temp_data.setdefault(CallbackEntry.sort, {}),
        )

    @property
    def captures(self) -> dict[str, CaptureEntry]:
        return cast(
            dict[str, CaptureEntry],
            self.data.setdefault(CaptureEntry.sort, {}),
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
    def lists(self) -> dict[str, ListEntry]:
        return cast(
            dict[str, ListEntry],
            self.data.setdefault(ListEntry.sort, {}),
        )

    @property
    def packages(self) -> dict[str, PackageEntry]:
        return cast(
            dict[str, PackageEntry],
            self.data.setdefault(PackageEntry.sort, {}),
        )

    @property
    def settings(self) -> dict[str, SettingEntry]:
        return cast(
            dict[str, SettingEntry],
            self.data.setdefault(SettingEntry.sort, {}),
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
            self._latest_package = entry

        # Track the current file:
        if isinstance(entry, FileEntry):
            self._latest_file = entry

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
        elif isinstance(entry, ActionEntry):
            # Actions are stored as action groups:
            action_group_entry = self.action_groups.get(entry.name, None)
            if action_group_entry is None:
                self.action_groups[entry.name] = entry.group()
            else:
                try:
                    action_group_entry.append(entry)
                except DuplicateEntry as e:
                    _LOGGER.exception(e)
        elif isinstance(entry, CommandEntry):
            # Commands are stored as lists:
            self.commands.append(entry)
        else:
            # Everything else is stored under its resolved name:
            self.data.setdefault(entry.sort, {})[entry.resolved_name] = entry

    def lookup(
        self, qualified_name: str, *, namespace: Optional[str] = None
    ) -> Optional[ObjectEntry]:
        """
        Look up an object entry by its qualifiedd name.
        """
        sort, name = qualified_name.split(":", maxsplit=1)
        resolved_name = resolve_name(name, namespace=namespace)
        return cast(
            Optional[ObjectEntry],
            self.data.get(sort, {}).get(resolved_name, None),
        )
