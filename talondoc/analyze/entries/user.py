import dataclasses
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, ClassVar, Mapping, Optional, TypeVar, Union, cast

import tree_sitter_talon
from typing_extensions import override

from ...util.logging import getLogger
from .abc import (
    ActionEntry,
    CaptureEntry,
    EventCode,
    GroupableObjectEntry,
    GroupEntry,
    ListEntry,
    ListValue,
    ModeEntry,
    ObjectEntry,
    SettingEntry,
    SettingValue,
    TagEntry,
)

_LOGGER = getLogger(__name__)


###############################################################################
# User-Defined Object Entries
###############################################################################


class UserObjectEntry(ObjectEntry):
    sort: ClassVar[str]
    mtime: Optional[float] = None
    location: Union[int, tuple[int, int], None] = None

    def __post_init__(self, *args, **kwargs):
        self.mtime = self.get_mtime()
        self.location = None

    @override
    def get_namespace(self) -> str:
        if isinstance(self, GroupEntry):
            for entry in self.entries():
                assert isinstance(
                    entry, ObjectEntry
                ), f"Unexpected value of type {type(entry)} in group"
                return entry.get_namespace()
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
    def get_location(self) -> str:
        if isinstance(self.location, int):
            line = self.location
            return f"{self.get_path()}: line {line}"
        if isinstance(self.location, tuple):
            line, column = self.location
            return f"{self.get_path()}: line {line}, column {column}"
        return f"{self.get_path()}"

    def set_location(self, location: Union[int, tuple[int, int], None]):
        self.location = location

    @override
    def same_as(self, other: "ObjectEntry") -> bool:
        if type(self) == type(other):
            if isinstance(self, UserPackageEntry):
                assert isinstance(other, UserPackageEntry)
                return self.name == other.name and self.path == other.path
            if isinstance(self, UserFileEntry):
                assert isinstance(other, UserFileEntry)
                return self.path == other.path
            if isinstance(other, UserObjectEntry):
                return (
                    self.get_resolved_name() == other.get_resolved_name()
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

    def get_file(self) -> Optional["UserFileEntry"]:
        if isinstance(self, UserPackageEntry):
            return None
        elif isinstance(self, UserFileEntry):
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

    def get_package(self) -> "UserPackageEntry":
        if isinstance(self, UserPackageEntry):
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
        if isinstance(self, UserPackageEntry):
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
    parent: Union["UserFileEntry", "UserModuleEntry"] = dataclasses.field(repr=False)

    @override
    def get_name(self) -> str:
        return self.name

    @override
    def group(self: "UserGroupableObjectEntry") -> "GroupEntry":
        if isinstance(self.parent, (UserTalonFileEntry, UserContextEntry)):
            return GroupEntry(default=None, overrides=[self])
        else:
            return GroupEntry(default=self, overrides=[])

    @override
    def is_override(self: "UserGroupableObjectEntry") -> bool:
        return isinstance(self.parent, (UserContextEntry, UserTalonFileEntry))


###############################################################################
# Callable Entries
###############################################################################


@dataclasses.dataclass
class UserFunctionEntry(UserObjectEntry):
    @override
    @classmethod
    def get_sort(cls) -> str:
        return "function"

    parent: "UserPythonFileEntry"
    func: Callable[..., Any] = dataclasses.field(repr=False)

    @override
    def get_name(self) -> str:
        return self.func.__qualname__

    @override
    def get_resolved_name(self) -> str:
        return f"{self.parent.get_name().removesuffix('.py')}.{self.get_name()}"


@dataclasses.dataclass
class UserCallbackEntry(UserObjectEntry):
    """Used to register callbacks into imported Python modules."""

    @override
    @classmethod
    def get_sort(cls) -> str:
        return "callback"

    parent: "UserPythonFileEntry"
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
class UserPackageEntry(UserObjectEntry):
    @override
    @classmethod
    def get_sort(cls) -> str:
        return "package"

    name: str
    path: Path
    files: list["UserFileEntry"] = dataclasses.field(default_factory=list)

    def __init__(
        self,
        path: Path,
        files: list["UserFileEntry"] = [],
        *,
        name: Optional[str] = None,
    ):
        self.path = path
        self.files = files
        self.name = UserPackageEntry.make_name(name, path)
        super().__post_init__(path, files, name=name)

    @staticmethod
    def make_name(name: Optional[str], path: Path) -> str:
        return name or path.parts[-1]

    @override
    def get_name(self) -> str:
        return self.name


AnyUserFileEntry = TypeVar("AnyUserFileEntry", bound="UserFileEntry")


@dataclasses.dataclass
class UserFileEntry(UserObjectEntry):
    @override
    @classmethod
    def get_sort(cls) -> str:
        return "file"

    parent: UserPackageEntry = dataclasses.field(repr=False)
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
    def make_name(package: UserPackageEntry, path: Path) -> str:
        return ".".join((package.get_namespace(), *path.parts))

    @override
    def get_name(self) -> str:
        return UserFileEntry.make_name(self.parent, self.path)


@dataclasses.dataclass
class UserTalonFileEntry(UserFileEntry):
    # TODO: extract docstring as desc
    commands: list["UserCommandEntry"] = dataclasses.field(default_factory=list)
    matches: Optional[tree_sitter_talon.TalonMatches] = None
    settings: list["UserSettingEntry"] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class UserPythonFileEntry(UserFileEntry):
    modules: list["UserModuleEntry"] = dataclasses.field(default_factory=list)


###############################################################################
# Module and Context Entries
###############################################################################

AnyUserModuleEntry = TypeVar("AnyUserModuleEntry", bound="UserModuleEntry")


@dataclasses.dataclass
class UserModuleEntry(UserObjectEntry):
    parent: UserPythonFileEntry = dataclasses.field(repr=False)
    desc: Optional[str]
    index: int = dataclasses.field(init=False)

    @override
    @classmethod
    def get_sort(cls) -> str:
        return "module"

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        self.index = len(self.parent.modules)
        self.parent.modules.append(self)

    @override
    def get_name(self) -> str:
        return ".".join(
            [
                self.get_namespace(),
                *self.parent.path.parts,
                str(self.index),
            ]
        )


@dataclasses.dataclass
class UserContextEntry(UserModuleEntry):
    sort: ClassVar[str] = "context"
    matches: Union[None, str, tree_sitter_talon.TalonMatches] = None


###############################################################################
# Command Entries
###############################################################################


@dataclasses.dataclass
class UserCommandEntry(UserObjectEntry):
    parent: UserTalonFileEntry = dataclasses.field(repr=False)
    ast: tree_sitter_talon.TalonCommandDeclaration

    @override
    @classmethod
    def get_sort(cls) -> str:
        return "command"

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        self._index = len(self.parent.commands)
        assert self not in self.parent.commands
        self.parent.commands.append(self)

    @override
    def get_name(self) -> str:
        return f"{self.parent.get_name()}.{self._index}"


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
class UserActionEntry(UserGroupableObjectEntry, ActionEntry):
    desc: Optional[str]
    func: Optional[str]

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        # TODO: add self to module
        # NOTE: fail fast if func is a <function>
        assert self.func is None or isinstance(self.func, str), "\n".join(
            [
                "Do not store Python function on UserActionEntry",
                "Register a UserFunctionEntry and use function_entry.name",
            ]
        )

    @override
    def get_function_name(self) -> Optional[str]:
        return self.func


@dataclasses.dataclass
class UserCaptureEntry(UserGroupableObjectEntry, CaptureEntry):
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

    @override
    def get_rule(self) -> Union[str, tree_sitter_talon.TalonRule]:
        return self.rule

    @override
    def get_function_name(self) -> Optional[str]:
        return self.func


@dataclasses.dataclass
class UserListEntry(UserGroupableObjectEntry, ListEntry):
    name: str
    desc: Optional[str] = None
    value: Optional[ListValue] = None

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        # TODO: add self to module
        self.value = _normalize_list_value(self.value)

    @override
    def get_value(self) -> Optional[ListValue]:
        return self.value


@dataclasses.dataclass
class UserModeEntry(UserObjectEntry, ModeEntry):
    name: str
    parent: UserModuleEntry = dataclasses.field(repr=False)
    desc: Optional[str] = None

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        # TODO: add self to module
        pass

    @override
    def get_name(self) -> str:
        return self.name


@dataclasses.dataclass
class UserSettingEntry(UserGroupableObjectEntry, SettingEntry):
    name: str
    type: Optional[str] = None
    desc: Optional[str] = None
    value: Optional[Union[SettingValue, tree_sitter_talon.TalonExpression]] = None

    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        # TODO: add self to module
        pass

    @override
    def get_value_type(self) -> Optional[str]:
        return self.type

    @override
    def get_value(
        self,
    ) -> Optional[Union[SettingValue, tree_sitter_talon.TalonExpression]]:
        return self.value


@dataclasses.dataclass
class UserTagEntry(UserObjectEntry, TagEntry):
    name: str
    parent: UserModuleEntry = dataclasses.field(repr=False)
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
