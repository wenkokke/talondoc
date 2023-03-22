from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, Mapping, Optional, Union, cast

import tree_sitter_talon
from dataclasses_json import dataclass_json
from typing_extensions import Literal, Protocol, Self, TypeAlias, TypeVar

from ...util.logging import getLogger

_LOGGER = getLogger(__name__)

##############################################################################
# Protocols
##############################################################################


class HasLastModified(Protocol):
    @property
    def last_modified(self) -> Optional[float]:
        ...


def is_newer_than(this: HasLastModified, that: HasLastModified) -> bool:
    if this.last_modified is None:
        return False
    if that.last_modified is None:
        return True
    return this.last_modified >= that.last_modified


##############################################################################
# Type Aliases
##############################################################################

ListValue: TypeAlias = Union[
    Mapping[str, Any],
    Iterable[str],
]

SettingValue: TypeAlias = Union[
    Any,
    tree_sitter_talon.TalonExpression,
]

EventCode: TypeAlias = Union[int, str]

Matches: TypeAlias = Union[
    None,
    str,
    tree_sitter_talon.TalonMatches,
]

Rule: TypeAlias = Union[
    str,
    tree_sitter_talon.TalonRule,
]

Script: TypeAlias = tree_sitter_talon.TalonBlock

##############################################################################
# Source Locations
##############################################################################


@dataclass_json
@dataclass(frozen=True)
class SrcLoc:
    path: Union[Literal["builtin"], Path]
    line: Optional[int] = None
    column: Optional[int] = None

    def __str__(self) -> str:
        if self.line is not None and self.column is not None:
            return f"{self.path}:{self.line}:{self.column}"
        if self.line is not None:
            return f"{self.path}:{self.line}"
        return f"{self.path}"


##############################################################################
# Abstract Base Classes
##############################################################################


_AnyFile = TypeVar("_AnyFile", bound=Union[Literal["builtin"], "File"])


@dataclass(frozen=True)
class _HasPackage:
    package: "Package" = field(repr=False)

    @property
    def namespace(self) -> str:
        return self.package.name


@dataclass(frozen=True)
class _HasFile(Generic[_AnyFile]):
    file: _AnyFile = field(repr=False)

    @property
    def name(self) -> str:
        if isinstance(self.file, File):
            return str(self.file.path)
        else:
            return cast(str, self.file)

    @property
    def location(self) -> SrcLoc:
        if isinstance(self.file, File):
            return self.file.location
        else:
            return SrcLoc(path=cast(Literal["builtin"], self.file))

    @property
    def last_modified(self) -> Optional[float]:
        if isinstance(self.file, File):
            return self.file.last_modified
        return None


@dataclass(frozen=True)
class _HasParent:
    parent: Union["Module", "Context"] = field(repr=False)

    @property
    def last_modified(self) -> Optional[float]:
        if self.parent:
            return self.parent.last_modified
        return None

    @property
    def file(self) -> Union[Literal["builtin"], "TalonFile", "PythonFile"]:
        return self.parent.file

    @property
    def namespace(self) -> str:
        return self.parent.namespace


@dataclass(frozen=True)
class _HasDescription:
    description: Optional[str]


@dataclass(frozen=True)
class _HasName(_HasParent):
    path: tuple[str, ...]

    @property
    def name(self) -> str:
        assert len(self.path) > 0, "Entry has empty name"
        resolved_name: tuple[str, ...]
        if self.path[0] == "self":
            resolved_name = (self.parent.namespace, *self.path[1:])
        else:
            resolved_name = self.path
        return ".".join(resolved_name)


@dataclass(frozen=True)
class _HasFunction:
    function_file: Optional["PythonFile"]
    function_name: Optional[str]
    function_type_hints: Optional[dict[str, type]]


@dataclass(frozen=True)
class _HasLocation:
    location: SrcLoc


@dataclass(frozen=True)
class _HasGroup(_HasName):
    group: "Group"[Self] = field(repr=False)

    @property
    def is_declaration(self) -> bool:
        return not self.is_override

    @property
    def is_override(self) -> bool:
        return isinstance(self.parent, Context)


_AnyHasGroup = TypeVar("_AnyHasGroup", bound=_HasGroup)


@dataclass_json
@dataclass(frozen=True)
class Group(
    Generic[_AnyHasGroup],
):
    declaration: Optional[_AnyHasGroup]
    override_list: list[_AnyHasGroup]

    @classmethod
    def singleton(cls, value: _AnyHasGroup) -> Self:
        if value.is_override:
            return cls(declaration=value, definition_list=[])
        else:
            return cls(declaration=None, definition_list=[value])


##############################################################################
# Packages
##############################################################################


@dataclass_json
@dataclass(frozen=True)
class Package:
    name: str
    path: Optional[Path]
    file_list: list["File"] = field(default_factory=list)

    @property
    def last_modified(self) -> Optional[float]:
        if self.path:
            return self.path.stat().st_mtime
        return None

    @property
    def location(self) -> SrcLoc:
        return SrcLoc(path=self.path or "builtin")


##############################################################################
# Files
##############################################################################


@dataclass_json
@dataclass(frozen=True)
class File(_HasPackage):
    path: Path

    @property
    def name(self) -> str:
        return ".".join((self.namespace, *self.path.parts))

    @property
    def last_modified(self) -> Optional[float]:
        return self.path.stat().st_mtime

    @property
    def location(self) -> SrcLoc:
        return SrcLoc(path=self.path)


@dataclass_json
@dataclass(frozen=True)
class TalonFile(File):
    context: "Context"
    command_list: list["Command"] = field(default_factory=list)
    setting_list: list["Setting"] = field(default_factory=list)


@dataclass_json
@dataclass(frozen=True)
class PythonFile(File):
    module_list: list["Module"] = field(default_factory=list)
    context_list: list["Context"] = field(default_factory=list)


##############################################################################
# Functions and Callbacks
##############################################################################


@dataclass(frozen=True)
class Function(_HasFile[PythonFile]):
    function_name: str
    function: Callable[..., Any] = field(repr=False)

    @property
    def location(self) -> SrcLoc:
        assert (
            self.file != "builtin"
        ), f"function '{self.function_name}' has file 'builtin'"
        return SrcLoc(path=self.file.path, line=self.function.__code__.co_firstlineno)


@dataclass(frozen=True)
class Callback(_HasFile[PythonFile]):
    event_code: EventCode
    function_name: str
    function: Callable[..., Any] = field(repr=False)

    @property
    def location(self) -> SrcLoc:
        return SrcLoc(path=self.file.path, line=self.function.__code__.co_firstlineno)


##############################################################################
# Modules and Contexts
##############################################################################


@dataclass_json
@dataclass(frozen=True)
class Module(
    _HasPackage,
    _HasFile[PythonFile],
    _HasDescription,
):
    pass


@dataclass_json
@dataclass(frozen=True)
class Context(
    _HasPackage,
    _HasFile[Union[TalonFile, PythonFile]],
    _HasDescription,
):
    matches: Matches


##############################################################################
# Commands
##############################################################################


@dataclass_json
@dataclass(frozen=True)
class Command(
    _HasFile[TalonFile],
    _HasLocation,
):
    rule: Rule
    script: Script


##############################################################################
# Objects
##############################################################################


@dataclass_json
@dataclass(frozen=True)
class Action(
    _HasGroup,
    _HasDescription,
    _HasParent,
    _HasFunction,
    _HasLocation,
):
    pass


@dataclass_json
@dataclass(frozen=True)
class Capture(
    _HasGroup,
    _HasDescription,
    _HasParent,
    _HasFunction,
    _HasLocation,
):
    rule: Rule


@dataclass_json
@dataclass(frozen=True)
class List(
    _HasGroup,
    _HasDescription,
    _HasParent,
    _HasLocation,
):
    value: Optional[ListValue]


@dataclass_json
@dataclass(frozen=True)
class Setting(
    _HasGroup,
    _HasDescription,
    _HasParent,
    _HasLocation,
):
    value: Optional[SettingValue]
    value_type_hint: Optional[type]


@dataclass_json
@dataclass(frozen=True)
class Mode(
    _HasName,
    _HasDescription,
    _HasParent,
    _HasLocation,
):
    pass


@dataclass_json
@dataclass(frozen=True)
class Tag(
    _HasName,
    _HasDescription,
    _HasParent,
    _HasLocation,
):
    pass
