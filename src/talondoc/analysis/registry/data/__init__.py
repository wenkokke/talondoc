import textwrap
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import partial
from inspect import Signature
from typing import Any, Literal, TypeAlias

import tree_sitter_talon
from tree_sitter_talon import Node as Node
from tree_sitter_talon import Point as Point
from tree_sitter_talon import TalonBlock, TalonMatch, TalonRule
from typing_extensions import TypeVar, final

from ...._util.logging import getLogger
from .abc import (
    Data,
    GroupData,
    GroupDataHasFunction,
    Location,
    SimpleData,
    asdict_location,
    parse_location,
    rule_name,
)
from .serialise import (
    JsonValue,
    asdict_class,
    asdict_opt,
    asdict_pickle,
    asdict_signature,
    parse_class,
    parse_dict,
    parse_field,
    parse_optfield,
    parse_pickle,
    parse_signature,
    parse_str,
    parse_type,
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

EventCode: TypeAlias = int | str
Script: TypeAlias = TalonBlock
ListValue: TypeAlias = dict[str, Any] | list[str]
SettingValue: TypeAlias = Any
Match: TypeAlias = TalonMatch
Rule: TypeAlias = TalonRule


##############################################################################
# Decoders - Common
##############################################################################

field_name = parse_field("name", parse_str)
field_description = parse_optfield("description", parse_str)
field_location = parse_field("location", parse_location)
field_optlocation = parse_optfield("location", parse_location)
field_parent_name = parse_field("parent_name", parse_str)
field_value_type_hint = parse_optfield("value_type_hint", parse_type)

##############################################################################
# Decoders - Matches
##############################################################################


def parse_matches(value: Any) -> Sequence[Match]:
    if isinstance(value, str):
        value = "\n".join([line.strip() for line in value.splitlines()])
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


field_matches = parse_field("matches", parse_matches)

##############################################################################
# Decoders - Rules
##############################################################################


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


field_rule = parse_field("rule", parse_rule)

##############################################################################
# Decoders - Scripts
##############################################################################


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


field_script = parse_field("script", parse_script)

##############################################################################
# Encoders/Decoders - List Values
##############################################################################


def asdict_list_value(value: ListValue) -> JsonValue:
    if isinstance(value, Mapping):
        return {key: asdict_pickle(val) for key, val in value.items()}
    return list(value)


def parse_list_value(
    value: JsonValue, *, context: dict[str, str] | None = None
) -> ListValue:
    if context is None:
        context = {}
    if isinstance(value, Mapping):
        return {
            key: parse_pickle(val, context=context)
            for key, val in parse_dict(value).items()
        }
    if isinstance(value, Sequence):
        return list(map(parse_str, value))
    raise TypeError(
        f"Expected dict[str, any] or List[str], found {type(value).__name__}"
    )


def field_list_value(value: JsonValue) -> ListValue | None:
    context: dict[str, str] = {
        "object_type": "list",
        "field_name": "value",
    }
    if isinstance(value, dict):
        context["object_name"] = str(value.get("name", None))

    return parse_optfield("value", partial(parse_list_value, context=context))(value)


##############################################################################
# Encoders/Decoders - Setting Values
##############################################################################


asdict_setting_value = asdict_pickle

parse_setting_value = parse_pickle


def field_setting_value(value: JsonValue) -> SettingValue | None:
    context: dict[str, str] = {
        "object_type": "setting",
        "field_name": "value",
    }
    if isinstance(value, dict):
        context["object_name"] = str(value.get("name", None))

    return parse_optfield("value", partial(parse_pickle, context=context))(value)


##############################################################################
# Packages
##############################################################################


@final
@dataclass(unsafe_hash=True)
class Package(SimpleData):
    files: list["FileName"] = field(default_factory=list, init=False, hash=False)

    name: PackageName
    description: None = field(default=None, init=False, hash=False)
    location: Location
    parent_name: None = field(default=None, init=False, hash=False)
    parent_type: None = field(default=None, init=False, hash=False)
    serialisable: bool = field(default=True, init=False, hash=False)


##############################################################################
# Files
##############################################################################


@final
@dataclass(unsafe_hash=True)
class File(SimpleData):
    modules: list["ModuleName"] = field(default_factory=list, init=False, hash=False)
    contexts: list["ContextName"] = field(default_factory=list, init=False, hash=False)

    name: FileName = field(init=False, hash=False)
    description: None = field(default=None, init=False, hash=False)
    location: Location
    parent_name: PackageName
    parent_type: type[Package] = field(default=Package, init=False, hash=False)
    serialisable: bool = field(default=True, init=False, hash=False)

    def __post_init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.name = ".".join((self.parent_name, *self.location.path.parts))
        super().__post_init__(*_args, **_kwargs)


##############################################################################
# Modules and Contexts
##############################################################################


@final
@dataclass(unsafe_hash=True)
class Module(SimpleData):
    index: int

    name: ModuleName = field(init=False, hash=False)
    description: str | None
    location: Location
    parent_name: FileName
    parent_type: type[File] = field(default=File, init=False, hash=False)
    serialisable: bool = field(default=True, init=False, hash=False)

    actions: list["ActionName"] = field(default_factory=list, init=False, hash=False)
    captures: list["CaptureName"] = field(default_factory=list, init=False, hash=False)
    lists: list["ListName"] = field(default_factory=list, init=False, hash=False)
    modes: list["ModeName"] = field(default_factory=list, init=False, hash=False)
    settings: list["CaptureName"] = field(default_factory=list, init=False, hash=False)
    tags: list["TagName"] = field(default_factory=list, init=False, hash=False)

    def __post_init__(self, *_args: Any, **_kwargs: Any) -> None:
        if self.index == 0:
            self.name = f"{self.parent_name}"
        else:
            self.name = f"{self.parent_name}.{self.index}"
        super().__post_init__(*_args, **_kwargs)

    def has_content(self) -> bool:
        return any(
            map(
                bool,
                [
                    self.actions,
                    self.captures,
                    self.lists,
                    self.modes,
                    self.tags,
                ],
            )
        )


@final
@dataclass(unsafe_hash=True)
class Context(SimpleData):
    index: int
    matches: list[Match]

    name: ContextName = field(init=False, hash=False)
    description: str | None
    location: Location
    parent_name: FileName
    parent_type: type[File] = field(default=File, init=False, hash=False)
    serialisable: bool = field(default=True, init=False, hash=False)

    commands: list["CommandName"] = field(default_factory=list, init=False, hash=False)
    actions: list["ActionName"] = field(default_factory=list, init=False, hash=False)
    captures: list["CaptureName"] = field(default_factory=list, init=False, hash=False)
    lists: list["ListName"] = field(default_factory=list, init=False, hash=False)
    modes: list["ModeName"] = field(default_factory=list, init=False, hash=False)
    settings: list["CaptureName"] = field(default_factory=list, init=False, hash=False)
    tags: list["TagName"] = field(default_factory=list, init=False, hash=False)

    def __post_init__(self, *_args: Any, **_kwargs: Any) -> None:
        if self.index == 0:
            self.name = f"{self.parent_name}"
        else:
            self.name = f"{self.parent_name}.{self.index}"
        super().__post_init__(*_args, **_kwargs)

    def has_content(self) -> bool:
        return any(
            map(
                bool,
                [
                    self.commands,
                    self.actions,
                    self.captures,
                    self.lists,
                    self.modes,
                    self.tags,
                ],
            )
        )

    @property
    def always_on(self) -> bool:
        return not self.matches


##############################################################################
# Common Decoders - Cont'd
##############################################################################

field_parent_type: Callable[[JsonValue], type[Module] | type[Context]] = parse_field(
    "parent_type", parse_class(Module, Context)
)


##############################################################################
# Functions
##############################################################################


@final
@dataclass(unsafe_hash=True)
class Function(SimpleData):
    namespace: str
    name: str = field(init=False, hash=False)
    description: str | None = field(init=False, hash=False)
    location: Location
    parent_name: ModuleName | ContextName
    parent_type: type[Module] | type[Context]
    serialisable: bool = field(default=False, init=False, hash=False)

    function: Callable[..., Any] = field(repr=False)

    def __post_init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.name = f"{self.parent_name}:{self.namespace}.{self.function.__name__}"
        self.description = self.function.__doc__
        super().__post_init__(*_args, **_kwargs)


##############################################################################
# Callbacks
##############################################################################


@final
@dataclass(unsafe_hash=True)
class Callback(Data):
    name: str = field(init=False, hash=False)
    description: str | None = field(init=False, hash=False)
    location: Location
    parent_name: FileName
    parent_type: type[File] = field(default=File, init=False, hash=False)
    serialisable: bool = field(default=False, init=False, hash=False)

    event_code: EventCode
    function: Callable[..., Any] = field(repr=False)

    def __post_init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.name = f"{self.parent_name}:{self.function.__name__}"
        self.description = self.function.__doc__
        super().__post_init__(*_args, **_kwargs)


CallbackVar = TypeVar("CallbackVar", bound=Callback)

##############################################################################
# Commands
##############################################################################


@final
@dataclass(unsafe_hash=True)
class Command(GroupData):
    rule: Rule
    script: Script

    name: str = field(init=False, hash=False)
    description: str | None
    location: Location
    parent_name: ContextName
    parent_type: type[Context] = field(default=Context, init=False, hash=False)
    serialisable: bool = field(default=True, init=False, hash=False)

    def __post_init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.name = rule_name(self.rule)
        super().__post_init__(*_args, **_kwargs)

    @classmethod
    def from_dict(cls, value: JsonValue) -> "Command":
        return Command(
            rule=field_rule(value),
            script=field_script(value),
            description=field_description(value),
            location=parse_field("location", Location.from_dict)(value),
            parent_name=field_parent_name(value),
        )

    def to_dict(self) -> dict[str, JsonValue]:
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


def field_action_function_signature(value: JsonValue) -> Signature | None:
    context: dict[str, str] = {
        "object_type": "action",
        "field_name": "function_signature",
    }
    if isinstance(value, dict):
        context["object_name"] = str(value.get("name", None))
    return parse_optfield(
        "function_signature", partial(parse_signature, context=context)
    )(value)


@final
@dataclass(unsafe_hash=True)
class Action(GroupDataHasFunction):
    function_name: FunctionName | None
    function_signature: Signature | None

    name: ActionName
    description: str | None
    location: Literal["builtin"] | Location
    parent_name: ModuleName | ContextName
    parent_type: type[Module] | type[Context]
    serialisable: bool = field(default=True, init=False, hash=False)

    @classmethod
    def from_dict(cls, value: JsonValue) -> "Action":
        return Action(
            function_name=None,
            function_signature=field_action_function_signature(value),
            name=field_name(value),
            description=field_description(value),
            location=field_location(value),
            parent_name=field_parent_name(value),
            parent_type=field_parent_type(value),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "function_name": None,
            "function_signature": asdict_opt(asdict_signature)(self.function_signature),
            "name": self.name,
            "description": self.description,
            "location": asdict_location(self.location),
            "parent_name": self.parent_name,
            "parent_type": self.parent_type.__name__,
        }


def field_capture_function_signature(value: JsonValue) -> Signature | None:
    context: dict[str, str] = {
        "object_type": "capture",
        "field_name": "default",
        "field_path": "function_signature.parameters",
    }
    if isinstance(value, dict):
        context["object_name"] = str(value.get("name", None))
    return parse_optfield(
        "function_signature", partial(parse_signature, context=context)
    )(value)


@final
@dataclass(unsafe_hash=True)
class Capture(GroupDataHasFunction):
    rule: Rule
    function_name: FunctionName | None
    function_signature: Signature | None

    name: CaptureName
    description: str | None
    location: Literal["builtin"] | Location
    parent_name: ModuleName | ContextName
    parent_type: type[Module] | type[Context]
    serialisable: bool = field(default=True, init=False, hash=False)

    @classmethod
    def from_dict(cls, value: JsonValue) -> "Capture":
        return Capture(
            rule=field_rule(value),
            function_name=None,
            function_signature=field_capture_function_signature(value),
            name=field_name(value),
            description=field_description(value),
            location=field_location(value),
            parent_name=field_parent_name(value),
            parent_type=field_parent_type(value),
        )

    def to_dict(self) -> dict[str, JsonValue]:
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
@dataclass(unsafe_hash=True)
class List(GroupData):
    value: ListValue | None
    value_type_hint: type[Any] | None

    name: ListName
    description: str | None
    location: None | Literal["builtin"] | Location
    parent_name: ModuleName | ContextName
    parent_type: type[Module] | type[Context]
    serialisable: bool = field(default=True, init=False, hash=False)

    def __post_init__(self, *_args: Any, **_kwargs: Any) -> None:
        if isinstance(self.value, Mapping):
            self.value = dict(self.value)
        elif isinstance(self.value, Iterable):
            self.value = list(self.value)
        else:
            if type(self.value).__name__ != "ObjectShim" and self.value is not None:
                _LOGGER.warning(  # type: ignore[unreachable]
                    f"List value for {self.name} should be "
                    f"list or dict, found {type(self.value)}"
                )
            self.value = None
        super().__post_init__(*_args, **_kwargs)

    @classmethod
    def from_dict(cls, value: JsonValue) -> "List":
        return List(
            value=field_list_value(value),
            value_type_hint=field_value_type_hint(value),
            name=field_name(value),
            description=field_description(value),
            location=field_optlocation(value),
            parent_name=field_parent_name(value),
            parent_type=field_parent_type(value),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "value": asdict_opt(asdict_list_value)(self.value),
            "value_type_hint": asdict_opt(asdict_class)(self.value_type_hint),
            "name": self.name,
            "description": self.description,
            "location": asdict_opt(asdict_location)(self.location),
            "parent_name": self.parent_name,
            "parent_type": self.parent_type.__name__,
        }


@final
@dataclass(unsafe_hash=True)
class Setting(GroupData):
    value: SettingValue | None
    value_type_hint: type[Any] | None

    name: SettingName
    description: str | None
    location: None | Literal["builtin"] | Location
    parent_name: ModuleName | ContextName
    parent_type: type[Module] | type[Context]
    serialisable: bool = field(default=True, init=False, hash=False)

    @classmethod
    def from_dict(cls, value: JsonValue) -> "Setting":
        return Setting(
            value=field_setting_value(value),
            value_type_hint=field_value_type_hint(value),
            name=field_name(value),
            description=field_description(value),
            location=field_optlocation(value),
            parent_name=field_parent_name(value),
            parent_type=field_parent_type(value),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "value": asdict_opt(asdict_pickle)(self.value),
            "value_type_hint": asdict_opt(asdict_class)(self.value_type_hint),
            "name": self.name,
            "description": self.description,
            "location": asdict_opt(asdict_location)(self.location),
            "parent_name": self.parent_name,
            "parent_type": self.parent_type.__name__,
        }


@final
@dataclass(unsafe_hash=True)
class Mode(SimpleData):
    name: ModeName
    description: str | None
    location: None | Literal["builtin"] | Location
    parent_name: ModuleName
    parent_type: type[Module] = field(default=Module, init=False, hash=False)
    serialisable: bool = field(default=True, init=False, hash=False)

    @classmethod
    def from_dict(cls, value: JsonValue) -> "Mode":
        return Mode(
            name=field_name(value),
            description=field_description(value),
            location=field_optlocation(value),
            parent_name=field_parent_name(value),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "description": self.description,
            "location": asdict_opt(asdict_location)(self.location),
            "parent_name": self.parent_name,
        }


@final
@dataclass(unsafe_hash=True)
class Tag(SimpleData):
    name: TagName
    description: str | None
    location: None | Literal["builtin"] | Location
    parent_name: ModuleName
    parent_type: type[Module] = field(default=Module, init=False, hash=False)
    serialisable: bool = field(default=True, init=False, hash=False)

    @classmethod
    def from_dict(cls, value: JsonValue) -> "Tag":
        return Tag(
            name=field_name(value),
            description=field_description(value),
            location=field_optlocation(value),
            parent_name=field_parent_name(value),
        )

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "name": self.name,
            "description": self.description,
            "location": asdict_opt(asdict_location)(self.location),
            "parent_name": self.parent_name,
        }
