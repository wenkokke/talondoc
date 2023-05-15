import textwrap
import typing
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from functools import singledispatch
from inspect import Signature
from typing import Any, Dict, Generic, Mapping, Optional, Sequence, Union

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
    asdict_location,
    rule_name,
)
from .serialise import (
    asdict_opt,
    asdict_signature,
    parse_class,
    parse_field,
    parse_optfield,
    parse_signature,
    parse_str,
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
Match: TypeAlias = TalonMatch
Rule: TypeAlias = TalonRule


##############################################################################
# Common Decoders
##############################################################################


def parse_matches(value: Any) -> Sequence[Match]:
    src = f"{parse_str(value)}\n-\n"
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


def parse_rule(value: Any) -> Rule:
    src = f"-\n{parse_str(value)}: skip\n"
    ast = tree_sitter_talon.parse(src, raise_parse_error=True)
    assert isinstance(ast, tree_sitter_talon.TalonSourceFile)
    for child in ast.children:
        if isinstance(child, tree_sitter_talon.TalonDeclarations):
            for declaration in child.children:
                if isinstance(declaration, tree_sitter_talon.TalonCommandDeclaration):
                    return declaration.left
    raise ValueError(f"Could not parse rule '{value}'")


def parse_script(value: Any) -> Script:
    src = f"-\nskip:\n{textwrap.indent(parse_str(value), '  ')}\n"
    ast = tree_sitter_talon.parse(src, raise_parse_error=True)
    assert isinstance(ast, tree_sitter_talon.TalonSourceFile)
    for child in ast.children:
        if isinstance(child, tree_sitter_talon.TalonDeclarations):
            for declaration in child.children:
                if isinstance(declaration, tree_sitter_talon.TalonCommandDeclaration):
                    return declaration.right
    raise ValueError(f"Could not parse script '{value}'")


field_signature = parse_optfield("function_signature", parse_signature)
field_name = parse_field("name", parse_str)
field_description = parse_optfield("description", parse_str)
field_location = parse_field("location", Location.from_dict)
field_parent_name = parse_field("parent_name", parse_str)
field_rule = parse_field("rule", parse_rule)
field_matches = parse_field("matches", parse_matches)
field_script = parse_field("script", parse_script)

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
            self.name = f"{self.parent_name}"
        else:
            self.name = f"{self.parent_name}.{self.index}"


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
            self.name = f"{self.parent_name}"
        else:
            self.name = f"{self.parent_name}.{self.index}"

    @property
    def always_on(self) -> bool:
        return not self.matches


##############################################################################
# Common Decoders - Cont'd
##############################################################################

field_parent_type: Callable[[Any], Union[type[Module], type[Context]]] = parse_field(
    "parent_type", parse_class(Module, Context)  # type: ignore[arg-type]
)


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
    rule: Rule
    script: Script

    name: str = field(init=False)
    description: Optional[str]
    location: Union[Literal["builtin"], Location]
    parent_name: ContextName
    parent_type: type[Context] = field(default=Context, init=False)
    serialisable: bool = field(default=True, init=False)

    def __post_init__(self, *_args, **_kwargs) -> None:
        self.name = rule_name(self.rule)

    @staticmethod
    def from_dict(value: Mapping[Any, Any]) -> "Command":
        return Command(
            rule=field_rule(value),
            script=field_script(value),
            description=field_description(value),
            location=field_location(value),
            parent_name=field_parent_name(value),
        )

    def to_dict(self) -> Mapping[Any, Any]:
        return {
            "rule": self.rule.text,
            "script": self.script.text,
            "description": self.description,
            "location": asdict_location(self.location),
            "parent_name": self.parent_name,
        }


##############################################################################
# Objects
##############################################################################


@final
@dataclass
class Action(GroupDataHasFunction):
    function_name: Optional[FunctionName]
    function_signature: Optional[Signature]

    name: ActionName
    description: Optional[str]
    location: Union[Literal["builtin"], Location]
    parent_name: Union[ModuleName, ContextName]
    parent_type: Union[type[Module], type[Context]]
    serialisable: bool = field(default=True, init=False)

    @staticmethod
    def from_dict(value: Mapping[Any, Any]) -> "Action":
        return Action(
            function_name=None,
            function_signature=field_signature(value),
            name=field_name(value),
            description=field_description(value),
            location=field_location(value),
            parent_name=field_parent_name(value),
            parent_type=field_parent_type(value),
        )

    def to_dict(self) -> Mapping[Any, Any]:
        return {
            "function_name": None,
            "function_signature": asdict_opt(asdict_signature)(self.function_signature),
            "name": self.name,
            "description": self.description,
            "location": asdict_location(self.location),
            "parent_name": self.parent_name,
            "parent_type": self.parent_type.__name__,
        }


@final
@dataclass
class Capture(GroupDataHasFunction):
    rule: Rule
    function_name: Optional[FunctionName]
    function_signature: Optional[Signature]

    name: CaptureName
    description: Optional[str]
    location: Union[Literal["builtin"], Location]
    parent_name: Union[ModuleName, ContextName]
    parent_type: Union[type[Module], type[Context]]
    serialisable: bool = field(default=True, init=False)

    @staticmethod
    def from_dict(value: Mapping[Any, Any]) -> "Capture":
        return Capture(
            rule=field_rule(value),
            function_name=None,
            function_signature=field_signature(value),
            name=field_name(value),
            description=field_description(value),
            location=field_location(value),
            parent_name=field_parent_name(value),
            parent_type=field_parent_type(value),
        )

    def to_dict(self) -> Mapping[Any, Any]:
        return {
            "rule": self.rule.text,
            "function_name": None,
            "function_signature": asdict_opt(asdict_signature)(self.function_signature),
            "name": self.name,
            "description": self.description,
            "location": asdict_location(self.location),
            "parent_name": self.parent_name,
            "parent_type": self.parent_type.__name__,
        }


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
