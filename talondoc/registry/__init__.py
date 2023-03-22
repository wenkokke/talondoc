from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import singledispatchmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union, cast, overload

from typing_extensions import Final, TypeAlias, TypeVar

from ..util.logging import getLogger
from . import entries as talon

_LOGGER = getLogger(__name__)

##############################################################################
# Entries
##############################################################################


# class Entry(Protocol):
#     @property
#     def name(self) -> str:
#         ...

#     @property
#     def location(self) -> talon.SrcLoc:
#         ...

Entry: TypeAlias = Union[
    talon.Package,
    talon.File,
    talon.Function,
    talon.Callback,
    talon.Module,
    talon.Context,
    talon.Command,
    talon.Action,
    talon.Capture,
    talon.List,
    talon.Setting,
    talon.Mode,
    talon.Tag,
]

_Entry = TypeVar("_Entry", bound=Entry)

SimpleEntry: TypeAlias = Union[
    talon.Package,
    talon.File,
    talon.Function,
    talon.Module,
    talon.Context,
    talon.Mode,
    talon.Tag,
]

_SimpleEntry = TypeVar("_SimpleEntry", bound=SimpleEntry)

GroupEntry: TypeAlias = Union[
    talon.Action,
    talon.Capture,
    talon.List,
    talon.Setting,
]

_GroupEntry = TypeVar("_GroupEntry", bound=GroupEntry)

##############################################################################
# Exceptions
##############################################################################


@dataclass(frozen=True)
class DuplicateEntry(Exception):
    """Raised when an entry is defined in multiple modules."""

    entry1: Entry
    entry2: Entry

    def __str__(self) -> str:
        class_name1 = self.entry1.__class__.__name__
        class_name2 = self.entry2.__class__.__name__
        if class_name1 != class_name2:
            _LOGGER.warning(
                f"DuplicateEntry exception with types {class_name1} and {class_name2}"
            )
        name1 = self.entry1.name
        name2 = self.entry2.name
        if class_name1 != class_name2:
            _LOGGER.warning(f"DuplicateEntry exception with names {name1} and {name2}")
        return "\n".join(
            [
                f"{class_name1} '{name1}' is declared twice:",
                f"- {self.entry1.location}",
                f"- {self.entry2.location}",
            ]
        )


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


@dataclass(init=False)
class Registry:
    data: Final[Dict[str, Any]]
    temp_data: Final[Dict[str, Any]]

    def __init__(self, data: Dict[str, Any], temp_data: Dict[str, Any]):
        self.data = data
        self.temp_data = temp_data

    active_package: Optional[talon.Package] = field(default=None, init=False)
    active_file: Optional[talon.File] = field(default=None, init=False)

    @property
    def packages(self) -> Dict[str, talon.Package]:
        return self.typed_data(talon.Package)

    @property
    def talon_files(self) -> Dict[str, talon.TalonFile]:
        return self.typed_data(talon.TalonFile)

    @property
    def python_files(self) -> Dict[str, talon.PythonFile]:
        return self.typed_data(talon.PythonFile)

    @property
    def functions(self) -> Dict[str, talon.Function]:
        return self.typed_data(talon.Function)

    @property
    def callbacks(self) -> Dict[talon.EventCode, List[talon.Callback]]:
        return self.typed_data(talon.Callback)

    @property
    def modules(self) -> Dict[str, talon.Module]:
        return self.typed_data(talon.Module)

    @property
    def contexts(self) -> Dict[str, talon.Context]:
        return self.typed_data(talon.Context)

    @property
    def commands(self) -> List[talon.Command]:
        return self.typed_data(talon.Command)

    @property
    def actions(self) -> Dict[str, talon.Group[talon.Action]]:
        return self.typed_data(talon.Action)

    @property
    def captures(self) -> Dict[str, talon.Group[talon.Capture]]:
        return self.typed_data(talon.Capture)

    @property
    def lists(self) -> Dict[str, talon.Group[talon.List]]:
        return self.typed_data(talon.List)

    @property
    def settings(self) -> Dict[str, talon.Group[talon.Setting]]:
        return self.typed_data(talon.Setting)

    @property
    def modes(self) -> Dict[str, talon.Mode]:
        return self.typed_data(talon.Mode)

    @property
    def tags(self) -> Dict[str, talon.Tag]:
        return self.typed_data(talon.Tag)

    @overload
    def typed_data(self, cls: type[_SimpleEntry]) -> Dict[str, _SimpleEntry]:
        ...

    @overload
    def typed_data(self, cls: type[_GroupEntry]) -> Dict[str, talon.Group[_GroupEntry]]:
        ...

    @overload
    def typed_data(
        self, cls: type[talon.Callback]
    ) -> Dict[talon.EventCode, List[talon.Callback]]:
        ...

    @overload
    def typed_data(self, cls: type[talon.Command]) -> List[talon.Command]:
        ...

    def typed_data(self, cls: type) -> Any:
        if issubclass(cls, (talon.Function, talon.Callback)):
            data = self.temp_data
        else:
            data = self.data
        if issubclass(cls, (talon.Command,)):
            return data.setdefault(cls.__name__, [])
        else:
            return data.setdefault(cls.__name__, {})

    @singledispatchmethod
    def register(self, value: Entry) -> None:
        raise TypeError(type(value))

    @register.register
    def _(self, value: talon.Package) -> None:
        self._register_simple_entry(talon.Package, value)

    @register.register
    def _(self, value: talon.TalonFile) -> None:
        self._register_simple_entry(talon.TalonFile, value)

    @register.register
    def _(self, value: talon.PythonFile) -> None:
        self._register_simple_entry(talon.PythonFile, value)

    @register.register
    def _(self, value: talon.Function) -> None:
        self._register_simple_entry(talon.Function, value)

    @register.register
    def _(self, value: talon.Module) -> None:
        self._register_simple_entry(talon.Module, value)

    @register.register
    def _(self, value: talon.Context) -> None:
        self._register_simple_entry(talon.Context, value)

    @register.register
    def _(self, value: talon.Action) -> None:
        self._register_group_entry(talon.Action, value)

    @register.register
    def _(self, value: talon.Capture) -> None:
        self._register_group_entry(talon.Capture, value)

    @register.register
    def _(self, value: talon.List) -> None:
        self._register_group_entry(talon.List, value)

    @register.register
    def _(self, value: talon.Setting) -> None:
        self._register_group_entry(talon.Setting, value)

    @register.register
    def _(self, value: talon.Mode) -> None:
        self._register_simple_entry(talon.Mode, value)

    @register.register
    def _(self, value: talon.Tag) -> None:
        self._register_simple_entry(talon.Tag, value)

    @register.register
    def _(self, value: talon.Callback) -> None:
        self.typed_data(talon.Callback).setdefault(value.event_code, []).append(value)

    @register.register
    def _(self, value: talon.Command) -> None:
        self.typed_data(talon.Command).append(value)

    def _register_simple_entry(self, cls: type[_SimpleEntry], value: _SimpleEntry):
        typed_data = self.typed_data(cls)
        old_value = typed_data.get(value.name, None)
        if old_value is not None:
            raise DuplicateEntry(value, old_value)
        typed_data[value.name] = value

    def _register_group_entry(self, cls: type[_GroupEntry], value: _GroupEntry) -> None:
        typed_data = self.typed_data(cls)
        old_group = typed_data.get(value.name)
        if old_group is None:
            typed_data[value.name] = talon.Group.singleton(value)
        else:
            if value.is_declaration:
                if old_group.declaration is None:
                    # Overwrite read-only attribute "declaration"
                    object.__setattr__(old_group, "declaration", value)
                else:
                    raise DuplicateEntry(value, old_group.declaration)
            else:
                old_group.override_list.append(value)

    # @contextmanager
    # def package(
    #     self,
    #     namespace: str,
    #     path: Optional[Path],
    # ) -> Iterator[tuple[bool, talon.Package]]:
    #     """
    #     Retrieve a package entry if it exists, or register a new package entry.
    #     """
    #     try:
    #         assert path.is_absolute()
    #         namespace = talon.Package.make_name(namespace, path)
    #         found_package_entry: bool = False
    #         for package_entry_name in list(self.packages.keys()):
    #             package_entry = self.packages[package_entry_name]
    #             if package_entry.name == namespace and package_entry.path == path:
    #                 if (
    #                     package_entry.mtime
    #                     and path.stat().st_mtime <= package_entry.mtime
    #                 ):
    #                     self.active_package_entry = package_entry
    #                     found_package_entry = True
    #                     yield (True, package_entry)
    #                 else:
    #                     del self.packages[package_entry_name]
    #         if not found_package_entry:
    #             package_entry = talon.Package(name=namespace, path=path)
    #             self.register(package_entry)
    #             self.active_package_entry = package_entry
    #             found_package_entry = True
    #             yield (False, package_entry)
    #     finally:
    #         # NOTE: a package remains active until the next package is opened
    #         pass

    # @contextmanager
    # def file_entry(
    #     self,
    #     cls: type[AnyFile],
    #     package: talon.Package,
    #     path: Path,
    # ) -> Iterator[tuple[bool, AnyFile]]:
    #     """
    #     Retrieve a file entry if it exists, or register a new file entry.
    #     """
    #     try:
    #         name = File.make_name(package, path)
    #         resolved_path = (package.path / path).resolve()
    #         file_entry = self.lookup("file", name)
    #         found_file_entry: bool = False
    #         if file_entry:
    #             if file_entry.newer_than(resolved_path.stat().st_mtime):
    #                 self.active_file_entry = file_entry
    #                 found_file_entry = True
    #                 yield (True, file_entry)
    #             else:
    #                 del self.files[name]
    #         if not found_file_entry:
    #             file_entry = cls(parent=package, path=path)  # type: ignore
    #             self.register(file_entry)
    #             self.active_file_entry = file_entry
    #             found_file_entry = True
    #             yield (False, file_entry)
    #     finally:
    #         self.active_file_entry = None

    # @property
    # def lookup(
    #     self, sort: Literal["action"], name: str, *, namespace: Optional[str] = None
    # ) -> Optional[talon.Group[talon.Action]]:
    #     ...

    # @property
    # def lookup(
    #     self, sort: Literal["capture"], name: str, *, namespace: Optional[str] = None
    # ) -> Optional[talon.Group[talon.Capture]]:
    #     ...

    # @property
    # def lookup(
    #     self, sort: Literal["list"], name: str, *, namespace: Optional[str] = None
    # ) -> Optional[talon.Group[talon.List]]:
    #     ...

    # @property
    # def lookup(
    #     self, sort: Literal["mode"], name: str, *, namespace: Optional[str] = None
    # ) -> Optional[talon.Mode]:
    #     ...

    # @property
    # def lookup(
    #     self, sort: Literal["setting"], name: str, *, namespace: Optional[str] = None
    # ) -> Optional[talon.Group[talon.Setting]]:
    #     ...

    # @property
    # def lookup(
    #     self, sort: Literal["tag"], name: str, *, namespace: Optional[str] = None
    # ) -> Optional[talon.Tag]:
    #     ...

    # @property
    # def lookup(
    #     self, sort: Literal["package"], name: str, *, namespace: Optional[str] = None
    # ) -> Optional[talon.Package]:
    #     ...

    # @property
    # def lookup(
    #     self, sort: Literal["file"], name: str, *, namespace: Optional[str] = None
    # ) -> Optional[AnyFile]:
    #     ...

    # @property
    # def lookup(
    #     self, sort: Literal["module"], name: str, *, namespace: Optional[str] = None
    # ) -> Sequence[talon.Module]:
    #     ...

    # @property
    # def lookup(
    #     self, sort: Literal["function"], name: str, *, namespace: Optional[str] = None
    # ) -> Optional[talon.Function]:
    #     ...

    # @property
    # def lookup(
    #     self, sort: Literal["callback"], name: str, *, namespace: Optional[str] = None
    # ) -> Sequence[Callback]:
    #     ...

    # def lookup(
    #     self,
    #     sort: Literal[
    #         "action",
    #         "capture",
    #         "list",
    #         "mode",
    #         "setting",
    #         "tag",
    #         "package",
    #         "file",
    #         "module",
    #         "function",
    #         "callback",
    #     ],
    #     name: str,
    #     *,
    #     namespace: Optional[str] = None
    # ) -> Any:
    #     """
    #     Look up an object entry by its name.
    #     """
    #     resolved_name = resolve_name(name, namespace=namespace)
    #     if sort in ("action", "capture", "list", "setting"):
    #         return self.groups.get(sort, {}).get(resolved_name, None)
    #     else:
    #         return self._data.get(sort, {}).get(resolved_name, None)

    # ##################################################
    # # The active GLOBAL registry
    # ##################################################

    # _active_global_registry: ClassVar[Optional["Registry"]]

    # @staticmethod
    # def get_active_global_registry() -> "Registry":
    #     try:
    #         if Registry._active_global_registry:
    #             return Registry._active_global_registry
    #     except AttributeError:
    #         pass
    #     raise NoActiveRegistry()

    # @staticmethod
    # def get_active_package() -> talon.Package:
    #     """
    #     Retrieve the active package.
    #     """
    #     registry = Registry.get_active_global_registry()
    #     if registry.active_package_entry:
    #         return registry.active_package_entry
    #     else:
    #         raise NoActivetalon.Package()

    # @staticmethod
    # def set_active_package(package_entry: talon.Package) -> None:
    #     """
    #     Set the active package.
    #     """
    #     registry = Registry.get_active_global_registry()
    #     registry.active_package_entry = package_entry

    # @staticmethod
    # def get_active_file() -> File:
    #     """
    #     Retrieve the active file.
    #     """
    #     registry = Registry.get_active_global_registry()
    #     if registry.active_file_entry:
    #         return registry.active_file_entry
    #     else:
    #         raise NoActiveFile()

    # @staticmethod
    # def set_active_file(file_entry: File) -> None:
    #     """
    #     Set the active file.
    #     """
    #     registry = Registry.get_active_global_registry()
    #     registry.active_file_entry = file_entry

    # def activate(self: Optional["Registry"]):
    #     """
    #     Set this registry as the current active registry.
    #     """
    #     Registry._active_global_registry = self
