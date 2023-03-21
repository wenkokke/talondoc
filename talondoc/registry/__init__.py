from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Literal, Optional, cast, overload

from ..util.logging import getLogger
from .entries.abc import (
    ActionEntry,
    AnyEntry,
    CaptureEntry,
    DuplicateEntry,
    Entry,
    GroupableObjectEntry,
    GroupEntry,
    ListEntry,
    ModeEntry,
    SettingEntry,
    TagEntry,
    resolve_name,
)
from .entries.user import (
    AnyUserFileEntry,
    EventCode,
    UserCallbackEntry,
    UserCommandEntry,
    UserContextEntry,
    UserFileEntry,
    UserFunctionEntry,
    UserModuleEntry,
    UserPackageEntry,
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

    _active_package_entry: Optional[UserPackageEntry] = field(default=None, init=False)

    _active_file_entry: Optional[UserFileEntry] = field(default=None, init=False)

    @contextmanager
    def as_active_package_entry(
        self, package_entry: UserPackageEntry
    ) -> Iterator[None]:
        try:
            self.active_package_entry = package_entry
            yield None
        finally:
            # NOTE: a package remains active until the next package is opened
            pass

    @contextmanager
    def package_entry(
        self,
        name: Optional[str],
        path: Path,
    ) -> Iterator[tuple[bool, UserPackageEntry]]:
        """
        Retrieve a package entry if it exists, or register a new package entry.
        """
        try:
            assert path.is_absolute()
            name = UserPackageEntry.make_name(name, path)
            found_package_entry: bool = False
            for package_entry_name in list(self.packages.keys()):
                package_entry = self.packages[package_entry_name]
                if package_entry.name == name and package_entry.path == path:
                    if (
                        package_entry.mtime
                        and path.stat().st_mtime <= package_entry.mtime
                    ):
                        self.active_package_entry = package_entry
                        found_package_entry = True
                        yield (True, package_entry)
                    else:
                        del self.packages[package_entry_name]
            if not found_package_entry:
                package_entry = UserPackageEntry(name=name, path=path)
                self.register(package_entry)
                self.active_package_entry = package_entry
                found_package_entry = True
                yield (False, package_entry)
        finally:
            # NOTE: a package remains active until the next package is opened
            pass

    @contextmanager
    def file_entry(
        self,
        cls: type[AnyUserFileEntry],
        package: UserPackageEntry,
        path: Path,
    ) -> Iterator[tuple[bool, AnyUserFileEntry]]:
        """
        Retrieve a file entry if it exists, or register a new file entry.
        """
        try:
            name = UserFileEntry.make_name(package, path)
            resolved_path = (package.path / path).resolve()
            file_entry = self.lookup("file", name)
            found_file_entry: bool = False
            if file_entry:
                if file_entry.newer_than(resolved_path.stat().st_mtime):
                    self.active_file_entry = file_entry
                    found_file_entry = True
                    yield (True, file_entry)
                else:
                    del self.files[name]
            if not found_file_entry:
                file_entry = cls(parent=package, path=path)  # type: ignore
                self.register(file_entry)
                self.active_file_entry = file_entry
                found_file_entry = True
                yield (False, file_entry)
        finally:
            self.active_file_entry = None

    @property
    def active_package_entry(self) -> Optional[UserPackageEntry]:
        return self._active_package_entry

    @active_package_entry.setter
    def active_package_entry(self, package_entry: UserPackageEntry) -> None:
        self._active_package_entry = package_entry

    @property
    def active_file_entry(self) -> Optional[UserFileEntry]:
        return self._active_file_entry

    @active_file_entry.setter
    def active_file_entry(self, file_entry: UserFileEntry) -> None:
        self._active_file_entry = file_entry

    @property
    def groups(self) -> dict[str, dict[str, GroupEntry]]:
        return cast(
            dict[str, dict[str, GroupEntry]],
            self.data.setdefault(GroupEntry.get_sort(), {}),
        )

    @property
    def action_groups(self) -> dict[str, GroupEntry[ActionEntry]]:
        return cast(
            dict[str, GroupEntry[ActionEntry]],
            self.groups.setdefault(ActionEntry.get_sort(), {}),
        )

    @property
    def capture_groups(self) -> dict[str, GroupEntry[CaptureEntry]]:
        return cast(
            dict[str, GroupEntry[CaptureEntry]],
            self.groups.setdefault(CaptureEntry.get_sort(), {}),
        )

    @property
    def list_groups(self) -> dict[str, GroupEntry[ListEntry]]:
        return cast(
            dict[str, GroupEntry[ListEntry]],
            self.groups.setdefault(ListEntry.get_sort(), {}),
        )

    @property
    def setting_groups(self) -> dict[str, GroupEntry[SettingEntry]]:
        return cast(
            dict[str, GroupEntry[SettingEntry]],
            self.groups.setdefault(SettingEntry.get_sort(), {}),
        )

    @property
    def callbacks(self) -> dict[EventCode, list[UserCallbackEntry]]:
        return cast(
            dict[EventCode, list[UserCallbackEntry]],
            self.temp_data.setdefault(UserCallbackEntry.get_sort(), {}),
        )

    @property
    def commands(self) -> list[UserCommandEntry]:
        return cast(
            list[UserCommandEntry],
            self.data.setdefault(UserCommandEntry.get_sort(), []),
        )

    @property
    def contexts(self) -> dict[str, list[UserContextEntry]]:
        return cast(
            dict[str, list[UserContextEntry]],
            self.data.setdefault(UserContextEntry.get_sort(), {}),
        )

    @property
    def files(self) -> dict[str, UserFileEntry]:
        return cast(
            dict[str, UserFileEntry],
            self.data.setdefault(UserFileEntry.get_sort(), {}),
        )

    @property
    def functions(self) -> dict[str, UserFunctionEntry]:
        return cast(
            dict[str, UserFunctionEntry],
            self.temp_data.setdefault(UserFunctionEntry.get_sort(), {}),
        )

    @property
    def modes(self) -> dict[str, ModeEntry]:
        return cast(
            dict[str, ModeEntry],
            self.data.setdefault(ModeEntry.get_sort(), {}),
        )

    @property
    def modules(self) -> dict[str, list[UserModuleEntry]]:
        return cast(
            dict[str, list[UserModuleEntry]],
            self.data.setdefault(UserModuleEntry.get_sort(), {}),
        )

    @property
    def packages(self) -> dict[str, UserPackageEntry]:
        return cast(
            dict[str, UserPackageEntry],
            self.data.setdefault(UserPackageEntry.get_sort(), {}),
        )

    @property
    def tags(self) -> dict[str, TagEntry]:
        return cast(
            dict[str, TagEntry],
            self.data.setdefault(TagEntry.get_sort(), {}),
        )

    def register(self, entry: Entry):
        """
        Register an object entry.
        """
        # Store the entry:
        if isinstance(entry, UserFunctionEntry):
            # Functions are TEMPORARY DATA, and are stored under their qualified names:
            if entry.get_resolved_name() in self.functions:
                e = DuplicateEntry(entry, self.functions[entry.get_resolved_name()])
                _LOGGER.warning(str(e))
            else:
                self.functions[entry.get_resolved_name()] = entry
        elif isinstance(entry, UserCallbackEntry):
            # Callbacks are TEMPORARY DATA, and are stored as lists under their event codes:
            self.callbacks.setdefault(entry.event_code, []).append(entry)
        elif isinstance(entry, GroupableObjectEntry):
            # Objects that can be overwritten are stored as groups:
            object_groups = self.groups.setdefault(entry.__class__.get_sort(), {})
            object_group = object_groups.get(entry.get_resolved_name(), None)
            if object_group:
                try:
                    object_group.append(entry)
                except DuplicateEntry as e:
                    _LOGGER.warning(str(e))
            else:
                object_groups[entry.get_resolved_name()] = entry.group()
        elif isinstance(entry, UserCommandEntry):
            # Commands are stored as lists:
            self.commands.append(entry)
        else:
            # Everything else is stored under its resolved name:
            self.data.setdefault(entry.get_sort(), {})[
                entry.get_resolved_name()
            ] = entry

    @overload
    def lookup(
        self, sort: Literal["action"], name: str, *, namespace: Optional[str] = None
    ) -> Optional[GroupEntry[ActionEntry]]:
        ...

    @overload
    def lookup(
        self, sort: Literal["capture"], name: str, *, namespace: Optional[str] = None
    ) -> Optional[GroupEntry[CaptureEntry]]:
        ...

    @overload
    def lookup(
        self, sort: Literal["list"], name: str, *, namespace: Optional[str] = None
    ) -> Optional[GroupEntry[ListEntry]]:
        ...

    @overload
    def lookup(
        self, sort: Literal["mode"], name: str, *, namespace: Optional[str] = None
    ) -> Optional[ModeEntry]:
        ...

    @overload
    def lookup(
        self, sort: Literal["setting"], name: str, *, namespace: Optional[str] = None
    ) -> Optional[GroupEntry[SettingEntry]]:
        ...

    @overload
    def lookup(
        self, sort: Literal["tag"], name: str, *, namespace: Optional[str] = None
    ) -> Optional[TagEntry]:
        ...

    @overload
    def lookup(
        self, sort: Literal["package"], name: str, *, namespace: Optional[str] = None
    ) -> Optional[UserPackageEntry]:
        ...

    @overload
    def lookup(
        self, sort: Literal["file"], name: str, *, namespace: Optional[str] = None
    ) -> Optional[AnyUserFileEntry]:
        ...

    @overload
    def lookup(
        self, sort: Literal["module"], name: str, *, namespace: Optional[str] = None
    ) -> Sequence[UserModuleEntry]:
        ...

    @overload
    def lookup(
        self, sort: Literal["function"], name: str, *, namespace: Optional[str] = None
    ) -> Optional[UserFunctionEntry]:
        ...

    @overload
    def lookup(
        self, sort: Literal["callback"], name: str, *, namespace: Optional[str] = None
    ) -> Sequence[UserCallbackEntry]:
        ...

    def lookup(
        self,
        sort: Literal[
            "action",
            "capture",
            "list",
            "mode",
            "setting",
            "tag",
            "package",
            "file",
            "module",
            "function",
            "callback",
        ],
        name: str,
        *,
        namespace: Optional[str] = None
    ) -> Any:
        """
        Look up an object entry by its name.
        """
        resolved_name = resolve_name(name, namespace=namespace)
        if sort in ("action", "capture", "list", "setting"):
            return self.groups.get(sort, {}).get(resolved_name, None)
        else:
            return self.data.get(sort, {}).get(resolved_name, None)

    ##################################################
    # The active GLOBAL registry
    ##################################################

    _active_global_registry: ClassVar[Optional["Registry"]]

    @staticmethod
    def get_active_global_registry() -> "Registry":
        try:
            if Registry._active_global_registry:
                return Registry._active_global_registry
        except AttributeError:
            pass
        raise NoActiveRegistry()

    @staticmethod
    def get_active_package() -> UserPackageEntry:
        """
        Retrieve the active package.
        """
        registry = Registry.get_active_global_registry()
        if registry.active_package_entry:
            return registry.active_package_entry
        else:
            raise NoActivePackage()

    @staticmethod
    def set_active_package(package_entry: UserPackageEntry) -> None:
        """
        Set the active package.
        """
        registry = Registry.get_active_global_registry()
        registry.active_package_entry = package_entry

    @staticmethod
    def get_active_file() -> UserFileEntry:
        """
        Retrieve the active file.
        """
        registry = Registry.get_active_global_registry()
        if registry.active_file_entry:
            return registry.active_file_entry
        else:
            raise NoActiveFile()

    @staticmethod
    def set_active_file(file_entry: UserFileEntry) -> None:
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
