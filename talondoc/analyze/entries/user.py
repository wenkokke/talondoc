import dataclasses
import pathlib
from collections.abc import Callable, Iterable
from typing import Any, ClassVar, Mapping, Optional, TypeVar, Union, cast

import tree_sitter_talon
from typing_extensions import override

from ...util.logging import getLogger
from .abc import (
    EventCode,
    GroupableObjectEntry,
    GroupEntry,
    ListValue,
    ObjectEntry,
    SettingValue,
)

_LOGGER = getLogger(__name__)


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
                docstring = entry.docstring
                if docstring is not None:
                    return docstring
        return None

    @override
    def get_location(self) -> str:
        return str(self.get_path())

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

    def get_path(self, absolute: bool = False) -> pathlib.Path:
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
1


@dataclasses.dataclass(
    init=False,
)
class PackageEntry(UserObjectEntry):
    sort: ClassVar[str] = "package"
    name: str
    path: pathlib.Path
    files: list["FileEntry"] = dataclasses.field(default_factory=list)

    def __init__(
        self,
        path: pathlib.Path,
        files: list["FileEntry"] = [],
        *,
        name: Optional[str] = None,
    ):
        self.path = path
        self.files = files
        self.name = PackageEntry.make_name(name, path)
        super().__post_init__(path, files, name=name)

    @staticmethod
    def make_name(name: Optional[str], path: pathlib.Path) -> str:
        return name or path.parts[-1]

    @override
    def get_name(self) -> str:
        return self.name


AnyFileEntry = TypeVar("AnyFileEntry", bound="FileEntry")


@dataclasses.dataclass
class FileEntry(UserObjectEntry):
    sort: ClassVar[str] = "file"
    parent: PackageEntry = dataclasses.field(repr=False)
    path: pathlib.Path

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
    def make_name(package: PackageEntry, path: pathlib.Path) -> str:
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
