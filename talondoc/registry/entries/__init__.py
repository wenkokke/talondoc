from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Generic, Mapping, Optional, Sequence, Union, cast

import tree_sitter_talon
from dataclasses_json import dataclass_json
from typing_extensions import Literal, Protocol, Self, TypeAlias, TypeVar, final

from ...util.logging import getLogger

_LOGGER = getLogger(__name__)


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


@final
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
        return resolve_path(self.path, self.parent.namespace)


def resolve_name(name: str, namespace: Optional[str]) -> str:
    return resolve_path(tuple(name.split(".")), namespace)


def resolve_path(path: Sequence[str], namespace: Optional[str]) -> str:
    assert len(path) > 0, "Entry has empty name"
    resolved_name: tuple[str, ...]
    if path[0] == "self":
        if namespace:
            resolved_name = (namespace, *path[1:])
        else:
            raise ValueError(f"encountered 'self', but 'namespace' was not provided")
    else:
        resolved_name = tuple(path)
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

    @property
    def always_matches(self) -> bool:
        return isinstance(self.parent, Context) and self.parent.always_matches


_AnyHasGroup = TypeVar("_AnyHasGroup", bound=_HasGroup)


@final
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
            return cls(declaration=value, override_list=[])
        else:
            return cls(declaration=None, override_list=[value])

    @property
    def always_matches(self) -> Optional[_AnyHasGroup]:
        for override in self.override_list:
            if override.always_matches:
                return override
        return None

    @property
    def default(self) -> Optional[_AnyHasGroup]:
        return self.declaration or self.always_matches

    def entries(self) -> Iterator[_AnyHasGroup]:
        if self.declaration:
            yield self.declaration
        yield from self.override_list


##############################################################################
# Packages
##############################################################################


@final
@dataclass_json
@dataclass(frozen=True)
class Package:
    name: str
    path: Optional[Path]
    file_list: list["File"] = field(init=False, default_factory=list)

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


@dataclass(frozen=True)
class File(_HasPackage):
    path: Path

    @staticmethod
    def make_name(path: Path, namespace: str) -> str:
        return ".".join((namespace, *path.parts))

    @property
    def name(self) -> str:
        return File.make_name(self.path, self.namespace)

    @property
    def last_modified(self) -> Optional[float]:
        return self.path.stat().st_mtime

    @property
    def location(self) -> SrcLoc:
        return SrcLoc(path=self.path)


@final
@dataclass_json
@dataclass(frozen=True)
class TalonFile(File):
    context: "Context"
    command_list: list["Command"] = field(init=False, default_factory=list)
    setting_list: list["Setting"] = field(init=False, default_factory=list)


@final
@dataclass_json
@dataclass(frozen=True)
class PythonFile(File):
    module_list: list["Module"] = field(init=False, default_factory=list)
    context_list: list["Context"] = field(init=False, default_factory=list)


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


@final
@dataclass_json
@dataclass(frozen=True)
class Module(
    _HasPackage,
    _HasFile[PythonFile],
    _HasDescription,
):
    pass


@final
@dataclass_json
@dataclass(frozen=True)
class Context(
    _HasPackage,
    _HasFile[Union[TalonFile, PythonFile]],
    _HasDescription,
):
    matches: Matches

    @cached_property
    def parsed_matches(self) -> Optional[tree_sitter_talon.TalonMatches]:
        if isinstance(self.matches, str):
            try:
                source = f"""{self.matches}\n-\n"""
                source_ast = tree_sitter_talon.parse(source, raise_parse_error=True)
                assert isinstance(source_ast, tree_sitter_talon.TalonSourceFile)
                for child in source_ast.children:
                    if isinstance(child, tree_sitter_talon.TalonMatches):
                        return child
                return None  # NOTE: self.matches declared no matches
            except (AssertionError, tree_sitter_talon.ParseError) as e:
                _LOGGER.exception(e)
                return None
        else:
            return self.matches

    @property
    def always_matches(self) -> bool:
        return self.parsed_matches is None or all(
            isinstance(child, tree_sitter_talon.TalonComment)
            for child in self.parsed_matches.children
        )


##############################################################################
# Commands
##############################################################################


@final
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


@final
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


@final
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


@final
@dataclass_json
@dataclass(frozen=True)
class List(
    _HasGroup,
    _HasDescription,
    _HasParent,
    _HasLocation,
):
    value: Optional[ListValue]


@final
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


@final
@dataclass_json
@dataclass(frozen=True)
class Mode(
    _HasName,
    _HasDescription,
    _HasParent,
    _HasLocation,
):
    pass


@final
@dataclass_json
@dataclass(frozen=True)
class Tag(
    _HasName,
    _HasDescription,
    _HasParent,
    _HasLocation,
):
    pass
