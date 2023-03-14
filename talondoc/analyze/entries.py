import abc
import dataclasses
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    Generic,
    Iterable,
    Mapping,
    Optional,
    TypeVar,
    Union,
    cast,
)

import tree_sitter_talon
from typing_extensions import override

from ..util.logging import getLogger

_LOGGER = getLogger(__name__)


###############################################################################
# Exceptions
###############################################################################


@dataclasses.dataclass(frozen=True)
class DuplicateEntry(Exception):
    """
    Raised when an entry is defined in multiple modules.
    """

    entry1: "ObjectEntry"
    entry2: "ObjectEntry"

    def __str__(self) -> str:
        sort = self.entry1.__class__.sort.capitalize()
        name = self.entry1.get_name()
        location1 = (
            f"{self.entry1.get_parent().sort}: {self.entry1.get_path()}"
            if isinstance(self.entry1, UserObjectEntry)
            else "builtin"
        )
        location2 = (
            f"{self.entry2.get_parent().sort}: {self.entry2.get_path()}"
            if isinstance(self.entry2, UserObjectEntry)
            else "builtin"
        )
        return "\n".join(
            [
                f"{sort} '{name}' is declared twice:",
                f"- {location1}",
                f"- {location2}",
            ]
        )


###############################################################################
# Basic Value Types
###############################################################################


ListValue = Union[Mapping[str, Any], Iterable[str]]


SettingValue = Any


###############################################################################
# Abstract Object Entries
###############################################################################


Entry = TypeVar("Entry", bound="ObjectEntry")


class ObjectEntry(abc.ABC):
    sort: ClassVar[str]

    @property
    def namespace(self) -> str:
        """The top-level namespace for this object, e.g., 'path' for 'path.talon_home'."""
        return self.get_namespace()

    @abc.abstractmethod
    def get_namespace(self) -> str:
        """The top-level namespace for this object, e.g., 'path' for 'path.talon_home'."""

    @property
    def resolved_name(self) -> str:
        """The resolved name for this object, including the top-level namespace."""
        return _resolve_name(self.get_name(), namespace=self.namespace)

    @abc.abstractmethod
    def get_name(self) -> str:
        """The name for this object, e.g., 'path.talon_home'."""

    @property
    def qualified_name(self) -> str:
        """The resolved name for this object prefixed by the sort of the object."""
        return f"{self.__class__.sort}:{self.resolved_name}"

    @abc.abstractmethod
    def get_docstring(self) -> Optional[str]:
        """The docstring for the object."""

    @property
    def docstring(self) -> Optional[str]:
        """The docstring for the object."""
        return self.get_docstring()

    @abc.abstractmethod
    def same_as(self, other: "ObjectEntry") -> bool:
        """Test whether or not this object sis the same as the other object."""

    @abc.abstractmethod
    def newer_than(self, other: Union[float, "ObjectEntry"]) -> bool:
        """Test whether or not this object is newer than the other object."""


GroupableObject = TypeVar("GroupableObject", bound="GroupableObjectEntry")


class GroupableObjectEntry(ObjectEntry):
    @abc.abstractmethod
    def group(self: "GroupableObject") -> "GroupEntry":
        """The group to which this object belongs."""

    @abc.abstractmethod
    def is_override(self: "GroupableObject") -> bool:
        """Test whether or not this object is an override."""


@dataclasses.dataclass
class GroupEntry(Generic[GroupableObject]):
    sort: ClassVar[str] = "group"
    default: Optional[GroupableObject] = None
    overrides: list[GroupableObject] = dataclasses.field(default_factory=list)

    @property
    def namespace(self) -> str:
        for entry in self.entries():
            return entry.namespace
        raise ValueError("Empty group")

    @property
    def resolved_name(self) -> str:
        for entry in self.entries():
            return entry.resolved_name
        raise ValueError("Empty group")

    def get_docstring(self) -> Optional[str]:
        for entry in self.entries():
            docstring = entry.get_docstring()
            if docstring is not None:
                return docstring
        return None

    def entries(self) -> Iterator[GroupableObject]:
        if self.default is not None:
            yield self.default
        yield from self.overrides

    def append(self, entry: "GroupableObject"):
        assert self.resolved_name == entry.resolved_name, "\n".join(
            [
                f"Cannot append entry with different name to a group:",
                f"- group name: {self.resolved_name}",
                f"- entry name: {entry.resolved_name}",
            ]
        )
        if entry.is_override():
            buffer: list[GroupableObject] = []
            replaced_older: bool = False
            for override in self.overrides:
                if entry.same_as(override):
                    if entry.newer_than(override):
                        replaced_older = True
                        buffer.append(entry)
                    else:
                        replaced_older = True
                        assert entry == override, "\n".join(
                            [
                                f"Found duplicate {entry.__class__.sort}:",
                                f"- {repr(entry)}",
                                f"- {repr(override)}",
                            ]
                        )
                else:
                    buffer.append(override)
            if not replaced_older:
                buffer.append(entry)
            self.overrides = buffer
        else:
            if self.default is not None:
                e = DuplicateEntry(self.default, entry)
                _LOGGER.error(str(e))
            self.default = entry


###############################################################################
# User-Defined Object Entries
###############################################################################


class UserObjectEntry(ObjectEntry):
    sort: ClassVar[str]
    mtime: Optional[float] = None

    def __post_init__(self, *args, **kwargs):
        self.mtime = self.get_mtime()

    @override
    def get_namespace(self) -> str:
        if isinstance(self, GroupEntry):
            for entry in self.entries():
                assert isinstance(
                    entry, ObjectEntry
                ), f"Unexpected value of type {type(entry)} in group"
                return entry.namespace
            raise ValueError("Empty group", self)
        else:
            return self.get_package().name

    @override
    def get_docstring(self) -> Optional[str]:
        if hasattr(self, "desc"):
            return cast(Optional[str], object.__getattribute__(self, "desc"))
        elif isinstance(self, GroupEntry):
            for entry in self.entries():
                assert isinstance(
                    entry, ObjectEntry
                ), f"Unexpected value of type {type(entry)} in group"
                docstring = entry.get_docstring()
                if docstring is not None:
                    return docstring
        return None

    @override
    def same_as(self, other: "ObjectEntry") -> bool:
        if type(self) == type(other):
            if isinstance(self, PackageEntry):
                assert isinstance(other, PackageEntry)
                return self.name == other.name and self.path == other.path
            if isinstance(self, FileEntry):
                assert isinstance(other, FileEntry)
                return self.path == other.path
            if isinstance(other, UserObjectEntry):
                return (
                    self.resolved_name == other.resolved_name
                    and self.get_parent().same_as(other.get_parent())
                )
        return False

    @override
    def newer_than(self, other: Union[float, "ObjectEntry"]) -> bool:
        assert self.mtime is not None, f"missing mtime on {self.__class__.sort}"
        if isinstance(other, float):
            return self.mtime >= other
        if isinstance(other, UserObjectEntry):
            assert other.mtime is not None, f"missing mtime on {other.__class__.sort}"
            return self.mtime >= other.mtime
        else:
            # NOTE: assumes that the other object must be a BuiltinObjectEntry
            return True

    def get_file(self) -> Optional["FileEntry"]:
        if isinstance(self, PackageEntry):
            return None
        elif isinstance(self, FileEntry):
            return self
        else:
            return self.get_parent().get_file()

    def get_mtime(self) -> float:
        try:
            if isinstance(self, GroupEntry):
                return max(
                    entry.get_mtime() if isinstance(entry, UserObjectEntry) else 0.0
                    for entry in self.entries()
                    if entry
                )
            else:
                return self.get_path(absolute=True).stat().st_mtime
        except FileNotFoundError as e:
            raise AssertionError(
                f"Could not stat '{self.__class__.sort}': {self.get_path(absolute=True)}"
            )

    def get_package(self) -> "PackageEntry":
        if isinstance(self, PackageEntry):
            return self
        else:
            file = self.get_file()
            assert file is not None
            return file.parent

    def get_parent(self) -> "UserObjectEntry":
        # NOTE: cannot use abstract properties with dataclasses
        try:
            return cast(UserObjectEntry, object.__getattribute__(self, "parent"))
        except AttributeError as e:
            raise ValueError(self, e)

    def get_path(self, absolute: bool = False) -> Path:
        if isinstance(self, PackageEntry):
            return self.path
        else:
            file = self.get_file()
            assert file is not None
            if absolute:
                # NOTE: relative to sphinx root
                return (file.parent.path / file.path).resolve()
            else:
                # NOTE: relative to package root
                return file.path


@dataclasses.dataclass
class UserGroupableObjectEntry(UserObjectEntry, GroupableObjectEntry):
    name: str
    parent: Union["FileEntry", "ModuleEntry"] = dataclasses.field(repr=False)

    @override
    def get_name(self) -> str:
        return self.name

    @override
    def group(self: "UserGroupableObjectEntry") -> "GroupEntry":
        if isinstance(self.parent, (TalonFileEntry, ContextEntry)):
            return GroupEntry(default=None, overrides=[self])
        else:
            return GroupEntry(default=self, overrides=[])

    @override
    def is_override(self: "UserGroupableObjectEntry") -> bool:
        return isinstance(self.parent, (ContextEntry, TalonFileEntry))


###############################################################################
# Callable Entries
###############################################################################


@dataclasses.dataclass
class FunctionEntry(UserObjectEntry):
    sort: ClassVar[str] = "function"
    parent: "PythonFileEntry"
    func: Callable[..., Any] = dataclasses.field(repr=False)

    @property
    def name(self) -> str:
        return self.get_name()

    @override
    def get_name(self) -> str:
        return self.func.__qualname__

    @property
    def resolved_name(self) -> str:
        return f"{self.parent.name.removesuffix('.py')}.{self.name}"


EventCode = Union[int, str]


@dataclasses.dataclass
class CallbackEntry(UserObjectEntry):
    """Used to register callbacks into imported Python modules."""

    sort: ClassVar[str] = "callback"
    parent: "PythonFileEntry"
    func: Callable[..., None] = dataclasses.field(repr=False)
    event_code: EventCode

    @override
    def get_name(self) -> str:
        return self.func.__qualname__


###############################################################################
# Package and File Entries
###############################################################################


@dataclasses.dataclass(
    init=False,
)
class PackageEntry(UserObjectEntry):
    sort: ClassVar[str] = "package"
    name: str
    path: Path
    files: list["FileEntry"] = dataclasses.field(default_factory=list)

    def __init__(
        self,
        path: Path,
        files: list["FileEntry"] = [],
        *,
        name: Optional[str] = None,
    ):
        self.path = path
        self.files = files
        self.name = PackageEntry.make_name(name, path)
        super().__post_init__(path, files, name=name)

    @staticmethod
    def make_name(name: Optional[str], path: Path) -> str:
        return name or path.parts[-1]

    @override
    def get_name(self) -> str:
        return self.name


AnyFileEntry = TypeVar("AnyFileEntry", bound="FileEntry")


@dataclasses.dataclass
class FileEntry(UserObjectEntry):
    sort: ClassVar[str] = "file"
    parent: PackageEntry = dataclasses.field(repr=False)
    path: Path

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        try:
            index = self.parent.files.index(self)
            _LOGGER.info(
                "\n".join(
                    [
                        f"[talondoc] file already analyzed:",
                        f" - {str(self.path)}",
                        f" - {str(self.parent.files[index].path)}",
                    ]
                )
            )
        except ValueError:
            self.parent.files.append(self)

    @staticmethod
    def make_name(package: PackageEntry, path: Path) -> str:
        return ".".join((package.namespace, *path.parts))

    @property
    def name(self) -> str:
        return self.get_name()

    @override
    def get_name(self) -> str:
        return FileEntry.make_name(self.parent, self.path)


@dataclasses.dataclass
class TalonFileEntry(FileEntry):
    # TODO: extract docstring as desc
    commands: list["CommandEntry"] = dataclasses.field(default_factory=list)
    matches: Optional[tree_sitter_talon.TalonMatches] = None
    settings: list["UserSettingEntry"] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class PythonFileEntry(FileEntry):
    modules: list["ModuleEntry"] = dataclasses.field(default_factory=list)


###############################################################################
# Module and Context Entries
###############################################################################

AnyModuleEntry = TypeVar("AnyModuleEntry", bound="ModuleEntry")


@dataclasses.dataclass
class ModuleEntry(UserObjectEntry):
    sort: ClassVar[str] = "module"
    parent: PythonFileEntry = dataclasses.field(repr=False)
    desc: Optional[str]
    index: int = dataclasses.field(init=False)

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        self.index = len(self.parent.modules)
        self.parent.modules.append(self)

    @property
    def name(self) -> str:
        return self.get_name()

    @override
    def get_name(self) -> str:
        return ".".join(
            [
                self.namespace,
                *self.parent.path.parts,
                str(self.index),
            ]
        )


@dataclasses.dataclass
class ContextEntry(ModuleEntry):
    sort: ClassVar[str] = "context"
    matches: Union[None, str, tree_sitter_talon.TalonMatches] = None


###############################################################################
# Command Entries
###############################################################################


@dataclasses.dataclass
class CommandEntry(UserObjectEntry):
    sort: ClassVar[str] = "command"
    parent: TalonFileEntry = dataclasses.field(repr=False)
    ast: tree_sitter_talon.TalonCommandDeclaration

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        self._index = len(self.parent.commands)
        assert self not in self.parent.commands
        self.parent.commands.append(self)

    @property
    def name(self) -> str:
        return self.get_name()

    @override
    def get_name(self) -> str:
        return f"{self.parent.name}.{self._index}"


###############################################################################
# Concrete Object Entries
# - Actions
# - Captures
# - Modes
# - Lists
# - Settings
# - Tags
###############################################################################


@dataclasses.dataclass
class UserActionEntry(UserGroupableObjectEntry):
    sort: ClassVar[str] = "action"
    desc: Optional[str]
    func: Optional[str]

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        # TODO: add self to module
        # NOTE: fail fast if func is a <function>
        assert self.func is None or isinstance(self.func, str), "\n".join(
            [
                "Do not store Python function on ActionEntry",
                "Register a FunctionEntry and use function_entry.name",
            ]
        )


@dataclasses.dataclass
class UserCaptureEntry(UserGroupableObjectEntry):
    sort: ClassVar[str] = "capture"
    name: str
    rule: Union[str, tree_sitter_talon.TalonRule]
    desc: Optional[str]
    func: Optional[str]

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        # TODO: add self to module
        # NOTE: fail fast if func is a <function>
        assert self.func is None or isinstance(self.func, str), "\n".join(
            [
                "Do not store Python function on CaptureEntry",
                "Register a FunctionEntry and use function_entry.name",
            ]
        )


@dataclasses.dataclass
class UserListEntry(UserGroupableObjectEntry):
    sort: ClassVar[str] = "list"
    name: str
    desc: Optional[str] = None
    value: Optional[ListValue] = None

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        # TODO: add self to module
        self.value = _normalize_list_value(self.value)


@dataclasses.dataclass
class UserModeEntry(UserObjectEntry):
    sort: ClassVar[str] = "mode"
    name: str
    parent: ModuleEntry = dataclasses.field(repr=False)
    desc: Optional[str] = None

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        # TODO: add self to module
        pass

    @override
    def get_name(self) -> str:
        return self.name


@dataclasses.dataclass
class UserSettingEntry(UserGroupableObjectEntry):
    sort: ClassVar[str] = "setting"
    name: str
    type: Optional[str] = None
    desc: Optional[str] = None
    value: Optional[Union[SettingValue, tree_sitter_talon.TalonExpression]] = None

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        # TODO: add self to module
        pass


@dataclasses.dataclass
class UserTagEntry(UserObjectEntry):
    sort: ClassVar[str] = "tag"
    name: str
    parent: ModuleEntry = dataclasses.field(repr=False)
    desc: Optional[str] = None

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        # TODO: add self to module
        pass

    @override
    def get_name(self) -> str:
        return self.name


###############################################################################
# Helper Functions
###############################################################################


def _normalize_list_value(list_value: ListValue) -> ListValue:
    if isinstance(list_value, Iterable):
        return list(list_value)
    elif isinstance(list_value, Mapping):
        return dict(list_value)
    elif list_value is not None:
        raise AssertionError(f"Value is not a list or dict: {list_value}")


def _resolve_name(name: str, *, namespace: Optional[str] = None) -> str:
    parts = name.split(".")
    if parts and parts[0] == "self":
        if namespace:
            return ".".join([namespace, *parts[1:]])
        else:
            raise ValueError(f"Cannot resolve 'self' in {name}")
    else:
        return name
