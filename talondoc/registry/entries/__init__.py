from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, Mapping, Optional, Sequence, Union

import tree_sitter_talon
from dataclasses_json import dataclass_json
from tree_sitter_talon import Node as Node
from tree_sitter_talon import Point as Point
from tree_sitter_talon import TalonBlock as Script
from tree_sitter_talon import TalonMatch as Match
from tree_sitter_talon import TalonRule as Rule
from typing_extensions import Literal, TypeVar, final, override

from ...util.logging import getLogger
from .abc import (
    ActionName,
    CallbackName,
    CaptureName,
    CommandName,
    ContextName,
    Data,
    EventCode,
    FileName,
    FunctionName,
    GroupData,
    GroupDataHasFunction,
    GroupDataVar,
    ListName,
    ListValue,
    Location,
    ModeName,
    ModuleName,
    PackageName,
    SettingName,
    SettingValue,
    SimpleData,
    TagName,
)

_LOGGER = getLogger(__name__)


##############################################################################
# Packages
##############################################################################


@final
@dataclass_json
@dataclass
class Package(SimpleData):
    _name: PackageName
    _location: Union[Literal["builtin"], Location]
    files: list["FileName"] = field(default_factory=list)

    @property
    @final
    @override
    def name(self) -> FileName:
        return self._name

    @property
    @final
    @override
    def description(self) -> None:
        return None

    @property
    @final
    @override
    def location(self) -> Union[Literal["builtin"], Location]:
        return self._location

    @property
    @final
    @override
    def parent_name(self) -> None:
        return None

    @property
    @final
    @override
    def parent_type(self) -> None:
        return None

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


##############################################################################
# Files
##############################################################################


@final
@dataclass_json
@dataclass
class File(SimpleData):
    _location: Location
    _parent_name: PackageName
    modules: list["ModuleName"] = field(default_factory=list)
    contexts: list["ContextName"] = field(default_factory=list)

    @property
    @final
    @override
    def name(self) -> FileName:
        return ".".join((self.parent_name, *self.location.path.parts))

    @property
    @final
    @override
    def description(self) -> None:
        return None

    @property
    @final
    @override
    def location(self) -> Location:
        return self._location

    @property
    @final
    @override
    def parent_name(self) -> str:
        return self._parent_name

    @property
    @final
    @override
    def parent_type(self) -> Literal["package"]:
        return "package"

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


##############################################################################
# Functions
##############################################################################


@final
@dataclass
class Function(SimpleData):
    function: Callable[..., Any] = field(repr=False)
    _location: Location
    _parent_name: FileName

    @property
    @final
    @override
    def name(self) -> FunctionName:
        return f"{self.parent_name}:{self.function.__name__}"

    @property
    @final
    @override
    def description(self) -> Optional[str]:
        return self.function.__doc__

    @property
    @final
    @override
    def location(self) -> Location:
        return self._location

    @property
    @final
    @override
    def parent_name(self) -> str:
        return self._parent_name

    @property
    @final
    @override
    def parent_type(self) -> Literal["file"]:
        return "file"

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return False


##############################################################################
# Callbacks
##############################################################################


@final
@dataclass
class Callback(Data):
    event_code: EventCode
    function: Callable[..., Any] = field(repr=False)
    _location: Location
    _parent_name: FileName

    @property
    @final
    @override
    def name(self) -> CallbackName:
        return f"{self.parent_name}:{self.function.__name__}"

    @property
    @final
    @override
    def description(self) -> Optional[str]:
        return self.function.__doc__

    @property
    @final
    @override
    def location(self) -> Location:
        return self._location

    @property
    @final
    @override
    def parent_name(self) -> str:
        return self._parent_name

    @property
    @final
    @override
    def parent_type(self) -> Literal["file"]:
        return "file"

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return False


CallbackVar = TypeVar("CallbackVar", bound=Callback)

##############################################################################
# Modules and Contexts
##############################################################################


@final
@dataclass_json
@dataclass
class Module(SimpleData):
    index: int
    _description: Optional[str]
    _location: Location
    _parent_name: FileName

    @property
    @final
    @override
    def name(self) -> ModuleName:
        return f"{self.parent_name}.module.{self.index}"

    @property
    @final
    @override
    def description(self) -> Optional[str]:
        return self._description

    @property
    @final
    @override
    def location(self) -> Location:
        return self._location

    @property
    @final
    @override
    def parent_name(self) -> str:
        return self._parent_name

    @property
    @final
    @override
    def parent_type(self) -> Literal["file"]:
        return "file"

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


@final
@dataclass_json
@dataclass
class Context(SimpleData):
    matches: list[Match]
    index: int
    _description: Optional[str]
    _location: Location
    _parent_name: FileName
    commands: list["CommandName"] = field(default_factory=list, init=False)

    @property
    @final
    @override
    def name(self) -> ContextName:
        return f"{self.parent_name}.context.{self.index}"

    @property
    @final
    @override
    def description(self) -> Optional[str]:
        return self._description

    @property
    @final
    @override
    def location(self) -> Location:
        return self._location

    @property
    @final
    @override
    def parent_name(self) -> str:
        return self._parent_name

    @property
    @final
    @override
    def parent_type(self) -> Literal["file"]:
        return "file"

    @final
    def is_default(self) -> bool:
        return False

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


def parse_matches(matches: str) -> Sequence[Match]:
    src = f"{matches}\n-\n"
    ast = tree_sitter_talon.parse(src, raise_parse_error=True)
    assert isinstance(ast, tree_sitter_talon.TalonSourceFile)
    for child in ast.children:
        if isinstance(child, tree_sitter_talon.TalonMatches):
            return [match for match in child.children if isinstance(match, Match)]
    return []


##############################################################################
# Commands
##############################################################################


@final
@dataclass_json
@dataclass
class Command(SimpleData):
    rule: Rule
    script: Script
    index: int
    _description: Optional[str]
    _location: Location
    _parent_name: ContextName

    @property
    def name(self) -> CommandName:
        return f"{self.parent_name}.command.{self.index}"

    @property
    @final
    @override
    def description(self) -> Optional[str]:
        return self._description

    @property
    @final
    @override
    def location(self) -> Location:
        return self._location

    @property
    @final
    @override
    def parent_name(self) -> str:
        return self._parent_name

    @property
    @final
    @override
    def parent_type(self) -> Literal["context"]:
        return "context"

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


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
# Objects
##############################################################################


@final
@dataclass_json
@dataclass
class Action(GroupDataHasFunction):
    _name: ActionName
    _description: Optional[str]
    _location: Union[Literal["builtin"], Location]
    _parent_name: Union[ModuleName, ContextName]
    _parent_type: Literal["module", "context"]
    _function_name: Optional[FunctionName]
    _function_type_hints: Optional[dict[str, type]]

    @property
    @final
    @override
    def name(self) -> str:
        return self._name

    @property
    @final
    @override
    def description(self) -> Optional[str]:
        return self._description

    @property
    @final
    @override
    def location(self) -> Union[Literal["builtin"], Location]:
        return self._location

    @property
    @final
    @override
    def parent_name(self) -> str:
        return self._parent_name

    @property
    @final
    @override
    def parent_type(self) -> Literal["module", "context"]:
        return self._parent_type

    @property
    @final
    @override
    def function_name(self) -> Optional[FunctionName]:
        return self._function_name

    @property
    @final
    @override
    def function_type_hints(self) -> Optional[Mapping[str, type]]:
        return self._function_type_hints

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


@final
@dataclass_json
@dataclass
class Capture(GroupDataHasFunction):
    rule: Rule
    _name: CaptureName
    _description: Optional[str]
    _location: Union[Literal["builtin"], Location]
    _parent_name: Union[ModuleName, ContextName]
    _parent_type: Literal["module", "context"]
    _function_name: Optional[FunctionName]
    _function_type_hints: Optional[dict[str, type]]

    @property
    @final
    @override
    def name(self) -> str:
        return self._name

    @property
    @final
    @override
    def description(self) -> Optional[str]:
        return self._description

    @property
    @final
    @override
    def location(self) -> Union[Literal["builtin"], Location]:
        return self._location

    @property
    @final
    @override
    def parent_name(self) -> str:
        return self._parent_name

    @property
    @final
    @override
    def parent_type(self) -> Literal["module", "context"]:
        return self._parent_type

    @property
    @final
    @override
    def function_name(self) -> Optional[FunctionName]:
        return self._function_name

    @property
    @final
    @override
    def function_type_hints(self) -> Optional[Mapping[str, type]]:
        return self._function_type_hints

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


@final
@dataclass_json
@dataclass
class List(GroupData):
    value: Optional[ListValue]
    value_type_hint: Optional[type]
    _name: ListName
    _description: Optional[str]
    _location: Union[Literal["builtin"], Location]
    _parent_name: Union[ModuleName, ContextName]
    _parent_type: Literal["module", "context"]

    @property
    @final
    @override
    def name(self) -> str:
        return self._name

    @property
    @final
    @override
    def description(self) -> Optional[str]:
        return self._description

    @property
    @final
    @override
    def location(self) -> Union[Literal["builtin"], Location]:
        return self._location

    @property
    @final
    @override
    def parent_name(self) -> str:
        return self._parent_name

    @property
    @final
    @override
    def parent_type(self) -> Literal["module", "context"]:
        return self._parent_type

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


@final
@dataclass_json
@dataclass
class Setting(GroupData):
    value: Optional[SettingValue]
    value_type_hint: Optional[type]
    _name: SettingName
    _description: Optional[str]
    _location: Union[Literal["builtin"], Location]
    _parent_name: Union[ModuleName, ContextName]
    _parent_type: Literal["module", "context"]

    @property
    @final
    @override
    def name(self) -> str:
        return self._name

    @property
    @final
    @override
    def description(self) -> Optional[str]:
        return self._description

    @property
    @final
    @override
    def location(self) -> Union[Literal["builtin"], Location]:
        return self._location

    @property
    @final
    @override
    def parent_name(self) -> str:
        return self._parent_name

    @property
    @final
    @override
    def parent_type(self) -> Literal["module", "context"]:
        return self._parent_type

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


@final
@dataclass_json
@dataclass
class Mode(SimpleData):
    _name: ModeName
    _description: Optional[str]
    _location: Union[Literal["builtin"], Location]
    _parent_name: ModuleName
    _parent_type: Literal["module"] = "module"

    @property
    @final
    @override
    def name(self) -> str:
        return self._name

    @property
    @final
    @override
    def description(self) -> Optional[str]:
        return self._description

    @property
    @final
    @override
    def location(self) -> Union[Literal["builtin"], Location]:
        return self._location

    @property
    @final
    @override
    def parent_name(self) -> str:
        return self._parent_name

    @property
    @final
    @override
    def parent_type(self) -> Literal["module"]:
        return self._parent_type

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


@final
@dataclass_json
@dataclass
class Tag(SimpleData):
    _name: TagName
    _description: Optional[str]
    _location: Union[Literal["builtin"], Location]
    _parent_name: ModuleName
    _parent_type: Literal["module"] = "module"

    @property
    @final
    @override
    def name(self) -> str:
        return self._name

    @property
    @final
    @override
    def description(self) -> Optional[str]:
        return self._description

    @property
    @final
    @override
    def location(self) -> Union[Literal["builtin"], Location]:
        return self._location

    @property
    @final
    @override
    def parent_name(self) -> str:
        return self._parent_name

    @property
    @final
    @override
    def parent_type(self) -> Literal["module"]:
        return self._parent_type

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


##############################################################################
# Groups
##############################################################################


@final
@dataclass_json
@dataclass
class Group(Generic[GroupDataVar]):
    declarations: list[GroupDataVar] = field(default_factory=list)
    overrides: list[GroupDataVar] = field(default_factory=list)

    def append(self, value: GroupDataVar) -> None:
        if value.parent_type == "module":
            self.declarations.append(value)
        else:
            self.overrides.append(value)
