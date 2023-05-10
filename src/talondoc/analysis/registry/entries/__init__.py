import typing
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, Mapping, Optional, Sequence, Union

import tree_sitter_talon
from tree_sitter_talon import Node as Node
from tree_sitter_talon import Point as Point
from tree_sitter_talon import TalonBlock, TalonMatch, TalonRule
from typing_extensions import Literal, TypeAlias, TypeVar, final

from ...._util.logging import getLogger
from .abc import (
    Data,
    GroupData,
    GroupDataHasFunction,
    GroupDataVar,
    Location,
    SimpleData,
)

_LOGGER = getLogger(__name__)


##############################################################################
# Type Aliases
##############################################################################

PackageName: TypeAlias = str
FileName: TypeAlias = str
FunctionName: TypeAlias = str
CallbackName: TypeAlias = str
ModuleName: TypeAlias = str
ContextName: TypeAlias = str
CommandName: TypeAlias = str
ActionName: TypeAlias = str
CaptureName: TypeAlias = str
ListName: TypeAlias = str
SettingName: TypeAlias = str
ModeName: TypeAlias = str
TagName: TypeAlias = str

EventCode: TypeAlias = Union[int, str]
Script: TypeAlias = TalonBlock
ListValue: TypeAlias = Union[typing.Dict[str, Any], typing.List[str]]
SettingValue: TypeAlias = Any


##############################################################################
# Parsing
##############################################################################


Match: TypeAlias = TalonMatch


def parse_matches(matches: str) -> Sequence[Match]:
    src = f"{matches}\n-\n"
    ast = tree_sitter_talon.parse(src, raise_parse_error=True)
    assert isinstance(ast, tree_sitter_talon.TalonSourceFile)
    for child in ast.children:
        if isinstance(child, tree_sitter_talon.TalonMatches):
            return [
                match
                for match in child.children
                if isinstance(match, tree_sitter_talon.TalonMatch)
            ]
    return []


Rule: TypeAlias = TalonRule


def parse_rule(rule: str) -> Rule:
    src = f"-\n{rule}: skip\n"
    ast = tree_sitter_talon.parse(src, raise_parse_error=True)
    assert isinstance(ast, tree_sitter_talon.TalonSourceFile)
    for child in ast.children:
        if isinstance(child, tree_sitter_talon.TalonDeclarations):
            for declaration in child.children:
                if isinstance(declaration, tree_sitter_talon.TalonCommandDeclaration):
                    return declaration.left
    return Rule("", "rule", Point(0, 0), Point(0, 0), [])


##############################################################################
# Packages
##############################################################################


@final
@dataclass
class Package(SimpleData):
    files: list["FileName"] = field(default_factory=list, init=False)

    name: PackageName
    description: None = field(default=None, init=False)
    location: Union[Literal["builtin"], Location]
    parent_name: None = field(default=None, init=False)
    parent_type: None = field(default=None, init=False)
    serialisable: bool = field(default=True, init=False)


##############################################################################
# Files
##############################################################################


@final
@dataclass
class File(SimpleData):
    modules: list["ModuleName"] = field(default_factory=list, init=False)
    contexts: list["ContextName"] = field(default_factory=list, init=False)

    name: FileName = field(init=False)
    description: None = field(default=None, init=False)
    location: Location
    parent_name: PackageName
    parent_type: type[Package] = field(default=Package, init=False)
    serialisable: bool = field(default=True, init=False)

    def __post_init__(self, *_args, **_kwargs) -> None:
        self.name = ".".join((self.parent_name, *self.location.path.parts))


##############################################################################
# Modules and Contexts
##############################################################################


@final
@dataclass
class Module(SimpleData):
    index: int

    name: ModuleName = field(init=False)
    description: Optional[str]
    location: Location
    parent_name: FileName
    parent_type: type[File] = field(default=File, init=False)
    serialisable: bool = field(default=True, init=False)

    def __post_init__(self, *_args, **_kwargs) -> None:
        if self.index == 0:
            self.name = f"{self.parent_name}.mod"
        else:
            self.name = f"{self.parent_name}.mod.{self.index}"


@final
@dataclass
class Context(SimpleData):
    index: int
    matches: list[Match]
    commands: list["CommandName"] = field(default_factory=list, init=False)

    name: ContextName = field(init=False)
    description: Optional[str]
    location: Location
    parent_name: FileName
    parent_type: type[File] = field(default=File, init=False)
    serialisable: bool = field(default=True, init=False)

    def __post_init__(self, *_args, **_kwargs) -> None:
        if self.index == 0:
            self.name = f"{self.parent_name}.ctx"
        else:
            self.name = f"{self.parent_name}.ctx.{self.index}"

    @property
    def always_on(self) -> bool:
        return not self.matches


##############################################################################
# Functions
##############################################################################


@final
@dataclass
class Function(SimpleData):
    namespace: str
    name: str = field(init=False)
    description: Optional[str] = field(init=False)
    location: Location
    parent_name: Union[ModuleName, ContextName]
    parent_type: Union[type[Module], type[Context]]
    serialisable: bool = field(default=False, init=False)

    function: Callable[..., Any] = field(repr=False)

    def __post_init__(self, *_args, **_kwargs) -> None:
        self.name = f"{self.parent_name}:{self.namespace}.{self.function.__name__}"
        self.description = self.function.__doc__


##############################################################################
# Callbacks
##############################################################################


@final
@dataclass
class Callback(Data):
    name: str = field(init=False)
    description: Optional[str] = field(init=False)
    location: Location
    parent_name: FileName
    parent_type: type[File] = field(default=File, init=False)
    serialisable: bool = field(default=False, init=False)

    event_code: EventCode
    function: Callable[..., Any] = field(repr=False)

    def __post_init__(self, *_args, **_kwargs) -> None:
        self.name = f"{self.parent_name}:{self.function.__name__}"
        self.description = self.function.__doc__


CallbackVar = TypeVar("CallbackVar", bound=Callback)


##############################################################################
# Commands
##############################################################################


@final
@dataclass
class Command(SimpleData):
    index: int
    rule: Rule
    script: Script

    name: str = field(init=False)
    description: Optional[str]
    location: Location
    parent_name: ContextName
    parent_type: type[Context] = field(default=Context, init=False)
    serialisable: bool = field(default=True, init=False)

    def __post_init__(self, *_args, **_kwargs) -> None:
        self.name = f"{self.parent_name}.cmd.{self.index}"


##############################################################################
# Objects
##############################################################################


@final
@dataclass
class Action(GroupDataHasFunction):
    function_name: Optional[FunctionName]
    function_type_hints: Optional[Mapping[str, type]]

    name: ActionName
    description: Optional[str]
    location: Union[Literal["builtin"], Location]
    parent_name: Union[ModuleName, ContextName]
    parent_type: Union[type[Module], type[Context]]
    serialisable: bool = field(default=True, init=False)


@final
@dataclass
class Capture(GroupDataHasFunction):
    rule: Rule
    function_name: Optional[FunctionName]
    function_type_hints: Optional[Mapping[str, type]]

    name: CaptureName
    description: Optional[str]
    location: Union[Literal["builtin"], Location]
    parent_name: Union[ModuleName, ContextName]
    parent_type: Union[type[Module], type[Context]]
    serialisable: bool = field(default=True, init=False)


@final
@dataclass
class List(GroupData):
    value: Optional[ListValue]
    value_type_hint: Optional[type]

    name: ListName
    description: Optional[str]
    location: Union[Literal["builtin"], Location]
    parent_name: Union[ModuleName, ContextName]
    parent_type: Union[type[Module], type[Context]]
    serialisable: bool = field(default=True, init=False)


@final
@dataclass
class Setting(GroupData):
    value: Optional[SettingValue]
    value_type_hint: Optional[type]

    name: SettingName
    description: Optional[str]
    location: Union[Literal["builtin"], Location]
    parent_name: Union[ModuleName, ContextName]
    parent_type: Union[type[Module], type[Context]]
    serialisable: bool = field(default=True, init=False)


@final
@dataclass
class Mode(SimpleData):
    name: ModeName
    description: Optional[str]
    location: Union[Literal["builtin"], Location]
    parent_name: ModuleName
    parent_type: type[Module] = field(default=Module, init=False)
    serialisable: bool = field(default=True, init=False)


@final
@dataclass
class Tag(SimpleData):
    name: TagName
    description: Optional[str]
    location: Union[Literal["builtin"], Location]
    parent_name: ModuleName
    parent_type: type[Module] = field(default=Module, init=False)
    serialisable: bool = field(default=True, init=False)


##############################################################################
# Groups
##############################################################################


@final
@dataclass
class Group(Generic[GroupDataVar]):
    declarations: list[GroupDataVar] = field(default_factory=list)
    overrides: list[GroupDataVar] = field(default_factory=list)

    def append(self, value: GroupDataVar) -> None:
        if issubclass(value.parent_type, Module):
            self.declarations.append(value)
        else:
            assert issubclass(value.parent_type, Context)
            self.overrides.append(value)
