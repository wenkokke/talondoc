import abc
import dataclasses
from collections.abc import Callable, Iterator, Sequence
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
        parent1 = self.entry1.get_parent().sort
        parent2 = self.entry1.get_parent().sort
        path1 = self.entry1.get_path()
        path2 = self.entry2.get_path()
        if parent1 == parent2 and path1 == path2:
            return "\n".join(
                [
                    f"{sort} '{name}' is declared twice in the same {parent1}:",
                    f"- {parent1}: {path1}",
                ]
            )
        else:
            return "\n".join(
                [
                    f"{sort} '{name}' is declared twice:",
                    f"- {parent1}: {path1}",
                    f"- {parent2}: {path2}",
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
    mtime: Optional[float] = None

    def __post_init__(self, *args, **kwargs):
        self.mtime = self.get_mtime()

    @property
    def namespace(self) -> str:
        if isinstance(self, GroupEntry):
            for entry in self.entries():
                return entry.namespace
            raise ValueError("Empty group entry", self)
        else:
            return self.get_package().name

    @property
    def resolved_name(self) -> str:
        return resolve_name(self.get_name(), namespace=self.namespace)

    @property
    def qualified_name(self) -> str:
        return f"{self.__class__.sort}:{self.resolved_name}"

    def get_docstring(self) -> Optional[str]:
        if hasattr(self, "desc"):
            return cast(Optional[str], object.__getattribute__(self, "desc"))
        elif isinstance(self, GroupEntry):
            for entry in self.entries():
                desc = entry.get_docstring()
                if desc:
                    return desc
        return None

    def get_file(self) -> Optional["FileEntry"]:
        if isinstance(self, PackageEntry):
            return None
        if isinstance(self, FileEntry):
            return self
        else:
            return self.get_parent().get_file()

    def get_name(self) -> str:
        # NOTE: cannot use abstract properties with dataclasses
        try:
            return cast(str, object.__getattribute__(self, "name"))
        except AttributeError as e:
            raise ValueError(self, e)

    def get_mtime(self) -> float:
        if isinstance(self, GroupEntry):
            return max(entry.get_mtime() for entry in self.entries() if entry)
        else:
            return self.get_path().stat().st_mtime

    def get_package(self) -> "PackageEntry":
        if isinstance(self, PackageEntry):
            return self
        else:
            file = self.get_file()
            assert file is not None
            return file.parent

    def get_parent(self) -> "ObjectEntry":
        # NOTE: cannot use abstract properties with dataclasses
        try:
            return cast(ObjectEntry, object.__getattribute__(self, "parent"))
        except AttributeError as e:
            raise ValueError(self, e)

    def get_path(self) -> Path:
        if isinstance(self, PackageEntry):
            return self.path
        else:
            file = self.get_file()
            assert file is not None
            return file.parent.path / file.path


CanOverride = TypeVar("CanOverride", bound="CanOverrideEntry")


@dataclasses.dataclass
class CanOverrideEntry(ObjectEntry):
    name: str
    parent: Union["FileEntry", "ModuleEntry"] = dataclasses.field(repr=False)

    def group(self: "CanOverride") -> "GroupEntry":  # ["CanOverride"]:
        if isinstance(self.parent, (TalonFileEntry, ContextEntry)):
            return GroupEntry(self.name, default=None, overrides=[self])
        else:
            return GroupEntry(self.name, default=self, overrides=[])


@dataclasses.dataclass
class GroupEntry(ObjectEntry, Generic[CanOverride]):
    sort: ClassVar[str] = "group"
    name: str
    default: Optional[CanOverride] = None
    overrides: list[CanOverride] = dataclasses.field(default_factory=list)

    def entries(self) -> Iterator[CanOverrideEntry]:
        if self.default:
            yield self.default
        yield from self.overrides

    def append(self, entry: "CanOverride"):
        assert self.resolved_name == entry.resolved_name, "\n".join(
            [
                f"Cannot append entry with different name to a group:",
                f"- group name: {self.resolved_name}",
                f"- entry name: {entry.resolved_name}",
            ]
        )
        if isinstance(entry.parent, ContextEntry):
            self.overrides.append(entry)
        elif isinstance(entry.parent, TalonFileEntry):
            self.overrides.append(entry)
        else:
            if self.default is not None:
                e = DuplicateEntry(self.default, entry)
                _LOGGER.error(str(e))
            self.default = entry


###############################################################################
# Callable Entries
###############################################################################


@dataclasses.dataclass
class FunctionEntry(ObjectEntry):
    sort: ClassVar[str] = "function"
    parent: "PythonFileEntry"
    func: Callable[..., Any] = dataclasses.field(repr=False)

    @property
    def name(self) -> str:
        return self.func.__qualname__

    @property
    def resolved_name(self) -> str:
        return f"{self.parent.name.removesuffix('.py')}.{self.name}"


EventCode = Union[int, str]


@dataclasses.dataclass
class CallbackEntry(ObjectEntry):
    """
    Used to register callbacks into imported Python modules.
    """

    sort: ClassVar[str] = "callback"
    parent: "PythonFileEntry"
    func: Callable[..., None] = dataclasses.field(repr=False)
    event_code: EventCode


###############################################################################
# Package and File Entries
###############################################################################


@dataclasses.dataclass(
    init=False,
)
class PackageEntry(ObjectEntry):
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

    @staticmethod
    def make_name(name: Optional[str], path: Path) -> str:
        return name or path.parts[-1]


AnyFileEntry = TypeVar("AnyFileEntry", bound="FileEntry")


@dataclasses.dataclass
class FileEntry(ObjectEntry):
    sort: ClassVar[str] = "file"
    parent: PackageEntry = dataclasses.field(repr=False)
    path: Path

    def __post_init__(self, *args, **kwargs):
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
        return FileEntry.make_name(self.parent, self.path)


@dataclasses.dataclass
class TalonFileEntry(FileEntry):
    # TODO: extract docstring as desc
    commands: list["CommandEntry"] = dataclasses.field(default_factory=list)
    matches: Optional[tree_sitter_talon.TalonMatches] = None
    settings: list["SettingEntry"] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class PythonFileEntry(FileEntry):
    modules: list["ModuleEntry"] = dataclasses.field(default_factory=list)


###############################################################################
# Module and Context Entries
###############################################################################

AnyModuleEntry = TypeVar("AnyModuleEntry", bound="ModuleEntry")


@dataclasses.dataclass
class ModuleEntry(ObjectEntry):
    sort: ClassVar[str] = "module"
    parent: PythonFileEntry = dataclasses.field(repr=False)
    desc: Optional[str]
    index: int = dataclasses.field(init=False)

    def __post_init__(self, *args, **kwargs):
        self.index = len(self.parent.modules)
        self.parent.modules.append(self)

    @property
    def name(self) -> str:
        return ".".join(
            [
                self.namespace,
                *self.parent.path.parts,
                str(self.index),
            ]
        )

    def __eq__(self, other):
        if type(self) == type(other):
            assert isinstance(other, ModuleEntry)
            return self.get_path() == other.get_path()
        return False


@dataclasses.dataclass
class ContextEntry(ModuleEntry):
    sort: ClassVar[str] = "context"
    matches: Union[None, str, tree_sitter_talon.TalonMatches] = None


###############################################################################
# Command Entries
###############################################################################


@dataclasses.dataclass
class CommandEntry(ObjectEntry):
    sort: ClassVar[str] = "command"
    parent: TalonFileEntry = dataclasses.field(repr=False)
    ast: tree_sitter_talon.TalonCommandDeclaration

    def __post_init__(self, *args, **kwargs):
        self._index = len(self.parent.commands)
        assert self not in self.parent.commands
        self.parent.commands.append(self)

    @property
    def name(self) -> str:
        return f"{self.parent.name}.{self._index}"

    def __eq__(self, other):
        if isinstance(other, CommandEntry):
            return (
                self.get_path() == other.get_path()
                and self.ast.start_position == other.ast.start_position
            )
        return False


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
class ActionEntry(CanOverrideEntry):
    sort: ClassVar[str] = "action"
    desc: Optional[str]
    func: Optional[str]

    def __post_init__(self, *args, **kwargs):
        # TODO: add self to module
        # NOTE: fail fast if func is a <function>
        assert self.func is None or isinstance(self.func, str), "\n".join(
            [
                "Do not store Python function on ActionEntry",
                "Register a FunctionEntry and use function_entry.name",
            ]
        )


@dataclasses.dataclass
class CaptureEntry(CanOverrideEntry):
    sort: ClassVar[str] = "capture"
    name: str
    rule: Union[str, tree_sitter_talon.TalonRule]
    desc: Optional[str]
    func: Optional[str]

    def __post_init__(self, *args, **kwargs):
        # TODO: add self to module
        # NOTE: fail fast if func is a <function>
        assert self.func is None or isinstance(self.func, str), "\n".join(
            [
                "Do not store Python function on CaptureEntry",
                "Register a FunctionEntry and use function_entry.name",
            ]
        )


@dataclasses.dataclass
class ListEntry(CanOverrideEntry):
    sort: ClassVar[str] = "list"
    name: str
    desc: Optional[str] = None
    value: Optional[ListValue] = None

    def __post_init__(self, *args, **kwargs):
        # TODO: add self to module
        self.value = normalize_list_value(self.value)


@dataclasses.dataclass
class ModeEntry(ObjectEntry):
    sort: ClassVar[str] = "mode"
    name: str
    parent: ModuleEntry = dataclasses.field(repr=False)
    desc: Optional[str] = None

    def __post_init__(self, *args, **kwargs):
        # TODO: add self to module
        pass


@dataclasses.dataclass
class SettingEntry(CanOverrideEntry):
    sort: ClassVar[str] = "setting"
    name: str
    type: Optional[str] = None
    desc: Optional[str] = None
    value: Optional[Union[SettingValue, tree_sitter_talon.TalonExpression]] = None

    def __post_init__(self, *args, **kwargs):
        # TODO: add self to module
        pass


@dataclasses.dataclass
class TagEntry(ObjectEntry):
    sort: ClassVar[str] = "tag"
    name: str
    parent: ModuleEntry = dataclasses.field(repr=False)
    desc: Optional[str] = None

    def __post_init__(self, *args, **kwargs):
        # TODO: add self to module
        pass


###############################################################################
# Helper Functions
###############################################################################


def normalize_list_value(list_value: ListValue) -> ListValue:
    if isinstance(list_value, Iterable):
        return list(list_value)
    elif isinstance(list_value, Mapping):
        return dict(list_value)
    elif list_value is not None:
        raise AssertionError(f"Value is not a list or dict: {list_value}")


def resolve_name(name: str, *, namespace: Optional[str] = None) -> str:
    parts = name.split(".")
    if parts and parts[0] == "self":
        if namespace:
            return ".".join([namespace, *parts[1:]])
        else:
            raise ValueError(f"Cannot resolve 'self' in {name}")
    else:
        return name
