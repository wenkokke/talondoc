from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import singledispatchmethod
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union, overload

from typing_extensions import Final, Protocol, TypeAlias, TypeGuard, TypeVar

from ..util.logging import getLogger
from . import entries as talon

_LOGGER = getLogger(__name__)

##############################################################################
# Entries
##############################################################################

Data: TypeAlias = Union[
    talon.Package,
    talon.TalonFile,
    talon.PythonFile,
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


_SimpleData = TypeVar(
    "_SimpleData",
    talon.Package,
    talon.TalonFile,
    talon.PythonFile,
    talon.Function,
    talon.Module,
    talon.Context,
    talon.Mode,
    talon.Tag,
)


_GroupData = TypeVar(
    "_GroupData",
    talon.Action,
    talon.Capture,
    talon.List,
    talon.Setting,
)


_File = TypeVar(
    "_File",
    talon.TalonFile,
    talon.PythonFile,
)


class HasLastModified(Protocol):
    @property
    def last_modified(self) -> Optional[float]:
        ...


def is_newer_than(
    this: HasLastModified, that: Union[None, float, Path, HasLastModified]
) -> bool:
    if this.last_modified is None:
        return False
    elif that is None:
        return True
    elif isinstance(that, float):
        return this.last_modified >= that
    elif isinstance(that, Path):
        return this.last_modified >= that.stat().st_mtime
    elif that.last_modified is None:
        return True
    else:
        return this.last_modified >= that.last_modified


##############################################################################
# Exceptions
##############################################################################


@dataclass(frozen=True)
class DuplicateData(Exception):
    """Raised when an entry is defined in multiple modules."""

    entry1: Data
    entry2: Data

    def __str__(self) -> str:
        class_name1 = self.entry1.__class__.__name__
        class_name2 = self.entry2.__class__.__name__
        if class_name1 != class_name2:
            _LOGGER.warning(
                f"DuplicateData exception with types {class_name1} and {class_name2}"
            )
        name1 = self.entry1.name
        name2 = self.entry2.name
        if class_name1 != class_name2:
            _LOGGER.warning(f"DuplicateData exception with names {name1} and {name2}")
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
    _data: Final[Dict[str, Any]]
    _temp_data: Final[Dict[str, Any]]

    _active_package: Optional[talon.Package]
    _active_file: Optional[talon.File]

    def __init__(self, data: Dict[str, Any], temp_data: Dict[str, Any]):
        self._data = data
        self._temp_data = temp_data
        self._active_package = None
        self._active_file = None

    ######################################################################
    # Register Data
    ######################################################################

    @singledispatchmethod
    def register(self, value: Data) -> None:
        raise TypeError(type(value))

    def _register_simple_data(self, value: _SimpleData) -> None:
        typed_data: Dict[str, _SimpleData] = self._typed_data(value.__class__)
        old_value = typed_data.get(value.name, None)
        if old_value is not None:
            raise DuplicateData(value, old_value)
        typed_data[value.name] = value

    def _register_group_data(self, value: _GroupData) -> None:
        typed_data = self._typed_data(value.__class__)
        old_group = typed_data.get(value.name)
        if old_group is None:
            typed_data[value.name] = talon.Group.singleton(value)
        else:
            if value.is_declaration:
                if old_group.declaration is None:
                    # Overwrite read-only attribute "declaration"
                    object.__setattr__(old_group, "declaration", value)
                else:
                    raise DuplicateData(value, old_group.declaration)
            else:
                old_group.override_list.append(value)

    def _register_callback(self, value: talon.Callback) -> None:
        self._typed_data(talon.Callback).setdefault(value.event_code, []).append(value)

    def _register_command(self, value: talon.Command) -> None:
        self._typed_data(talon.Command).append(value)

    # Simple entries
    register.register(talon.Package, _register_simple_data)
    register.register(talon.TalonFile, _register_simple_data)
    register.register(talon.PythonFile, _register_simple_data)
    register.register(talon.Function, _register_simple_data)
    register.register(talon.Module, _register_simple_data)
    register.register(talon.Context, _register_simple_data)
    register.register(talon.Mode, _register_simple_data)
    register.register(talon.Tag, _register_simple_data)

    # Group entries
    register.register(talon.Action, _register_group_data)
    register.register(talon.Capture, _register_group_data)
    register.register(talon.List, _register_group_data)
    register.register(talon.Setting, _register_group_data)

    # Other entries
    register.register(talon.Callback, _register_callback)
    register.register(talon.Command, _register_command)

    ######################################################################
    # Look Data Up
    ######################################################################

    def lookup(
        self, cls: type[_SimpleData], name: str, *, namespace: Optional[str] = None
    ) -> Optional[_SimpleData]:
        return self._typed_data(cls).get(talon.resolve_name(name, namespace))

    def lookup_group(
        self, cls: type[_GroupData], name: str, *, namespace: Optional[str] = None
    ) -> Optional[talon.Group[_GroupData]]:
        return self._typed_data(cls).get(talon.resolve_name(name, namespace))

    ######################################################################
    # Typed Access To Data
    ######################################################################

    @property
    def packages(self) -> Mapping[str, talon.Package]:
        return self._typed_data(talon.Package)

    @property
    def talon_files(self) -> Mapping[str, talon.TalonFile]:
        return self._typed_data(talon.TalonFile)

    @property
    def python_files(self) -> Mapping[str, talon.PythonFile]:
        return self._typed_data(talon.PythonFile)

    @property
    def functions(self) -> Mapping[str, talon.Function]:
        return self._typed_data(talon.Function)

    @property
    def callbacks(self) -> Mapping[talon.EventCode, Sequence[talon.Callback]]:
        return self._typed_data(talon.Callback)

    @property
    def modules(self) -> Mapping[str, talon.Module]:
        return self._typed_data(talon.Module)

    @property
    def contexts(self) -> Mapping[str, talon.Context]:
        return self._typed_data(talon.Context)

    @property
    def commands(self) -> Sequence[talon.Command]:
        return self._typed_data(talon.Command)

    @property
    def actions(self) -> Mapping[str, talon.Group[talon.Action]]:
        return self._typed_data(talon.Action)

    @property
    def captures(self) -> Mapping[str, talon.Group[talon.Capture]]:
        return self._typed_data(talon.Capture)

    @property
    def lists(self) -> Mapping[str, talon.Group[talon.List]]:
        return self._typed_data(talon.List)

    @property
    def settings(self) -> Mapping[str, talon.Group[talon.Setting]]:
        return self._typed_data(talon.Setting)

    @property
    def modes(self) -> Mapping[str, talon.Mode]:
        return self._typed_data(talon.Mode)

    @property
    def tags(self) -> Mapping[str, talon.Tag]:
        return self._typed_data(talon.Tag)

    @overload
    def _typed_data(self, cls: type[_SimpleData]) -> Dict[str, _SimpleData]:
        ...

    @overload
    def _typed_data(self, cls: type[_GroupData]) -> Dict[str, talon.Group[_GroupData]]:
        ...

    @overload
    def _typed_data(
        self, cls: type[talon.Callback]
    ) -> Dict[talon.EventCode, List[talon.Callback]]:
        ...

    @overload
    def _typed_data(self, cls: type[talon.Command]) -> List[talon.Command]:
        ...

    def _typed_data(self, cls: type) -> Any:
        # NOTE: functions and callbacks are temporary because they cannot be pickled
        if cls is talon.Function or cls is talon.Callback:
            data = self._temp_data
        else:
            data = self._data

        # NOTE: commands are stored in a list because they don't have a canonical name
        if cls is talon.Command:
            return data.setdefault(cls.__name__, [])  # type: ignore
        else:
            return data.setdefault(cls.__name__, {})  # type: ignore

    ######################################################################
    # Register If Missing
    ######################################################################

    def _lookup_or_register(
        self,
        cls: type[_SimpleData],
        new: Callable[[], _SimpleData],
        name: str,
        last_modified: Union[None, float, Path],
    ) -> tuple[bool, _SimpleData]:
        """Retrieve a value if it exists, or make and registerr register a new instance."""
        value = self.lookup(cls, name)
        if value is not None and is_newer_than(value, last_modified):
            assert value.name == name
            return (True, value)
        else:
            if value is not None:
                # TODO: delete all data related to that value
                del self._typed_data(cls)[name]
            value = new()
            self.register(value)
            return (False, value)

    @contextmanager
    def package(
        self,
        name: str,
        path: Optional[Path],
    ) -> Iterator[tuple[bool, talon.Package]]:
        """Retrieve a package if it exists, or register a new package."""
        try:
            assert not path or path.is_absolute()
            new = lambda: talon.Package(name, path)
            cached, package = self._lookup_or_register(talon.Package, new, name, path)
            self._active_package = package
            yield (cached, package)
        finally:
            # NOTE: a package remains active until the next package is opened
            pass

    @contextmanager
    def talon_file(
        self,
        path: Path,
        context: talon.Context,
        package: Optional[talon.Package] = None,
    ) -> Iterator[tuple[bool, talon.TalonFile]]:
        """Retrieve a file if it exists, or register a new file."""
        try:
            package = package or self._active_package
            if package is not None:
                not_none = package
            else:
                raise ValueError("no active package and package not provided")
            name = talon.File.make_name(path, not_none.name)
            new = lambda: talon.TalonFile(package=not_none, path=path, context=context)
            cached, file = self._lookup_or_register(talon.TalonFile, new, name, path)
            self._active_file = file
            yield (cached, file)
        finally:
            self._active_file = None

    @contextmanager
    def python_file(
        self,
        path: Path,
        package: Optional[talon.Package] = None,
    ) -> Iterator[tuple[bool, talon.PythonFile]]:
        """Retrieve a file if it exists, or register a new file."""
        try:
            package = package or self._active_package
            if package is not None:
                not_none = package
            else:
                raise ValueError("no active package and package not provided")
            name = talon.File.make_name(path, not_none.name)
            new = lambda: talon.PythonFile(package=not_none, path=path)
            cached, file = self._lookup_or_register(talon.PythonFile, new, name, path)
            self._active_file = file
            yield (cached, file)
        finally:
            self._active_file = None

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
