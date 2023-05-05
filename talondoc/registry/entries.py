from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, Mapping, Optional, Sequence, Union

import tree_sitter_talon
from dataclasses_json import dataclass_json
from tree_sitter_talon import Node as Node
from tree_sitter_talon import Point as Point
from tree_sitter_talon import TalonBlock as Script
from tree_sitter_talon import TalonExpression as Expression
from tree_sitter_talon import TalonMatch as Match
from tree_sitter_talon import TalonRule as Rule
from typing_extensions import Literal, TypeAlias, TypeGuard, TypeVar, final, override

from ..util.logging import getLogger

_LOGGER = getLogger(__name__)


##############################################################################
# Abstact Data
##############################################################################


class Data(metaclass=ABCMeta):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> Optional[str]:
        ...

    @property
    @abstractmethod
    def location(self) -> Union[Literal["builtin"], "Location"]:
        ...

    @property
    @abstractmethod
    def parent_name(self) -> Optional[str]:
        ...

    @property
    @abstractmethod
    def parent_type(self) -> Optional[Literal["package", "file", "module", "context"]]:
        ...

    @classmethod
    @abstractmethod
    def is_serialisable(cls) -> bool:
        ...


DataVar = TypeVar("DataVar", bound=Data)

##############################################################################
# Packages
##############################################################################

PackageName: TypeAlias = str


@final
@dataclass_json
@dataclass
class Package(Data):
    name: PackageName
    location: Union[Literal["builtin"], "Location"]

    parent_name: None = None
    parent_type: None = None

    files: list["FileName"] = field(default_factory=list)

    @property
    @final
    @override
    def description(self) -> None:
        return None

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


##############################################################################
# Files
##############################################################################

FileName: TypeAlias = str


@final
@dataclass_json
@dataclass
class File(Data):
    location: "Location"

    parent_name: PackageName
    parent_type: Literal["package"] = "package"

    modules: list["ModuleName"] = field(default_factory=list)
    contexts: list["ContextName"] = field(default_factory=list)

    @property
    @final
    @override
    def name(self) -> FileName:
        return ".".join(self.location.path.parts)

    @property
    @final
    @override
    def description(self) -> None:
        return None

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


##############################################################################
# Functions
##############################################################################

FunctionName: TypeAlias = str


@final
@dataclass
class Function(Data):
    function: Callable[..., Any] = field(repr=False)

    location: "Location"

    parent_name: FileName
    parent_type: Literal["file"]

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

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return False


##############################################################################
# Callbacks
##############################################################################

CallbackName: TypeAlias = str

EventCode: TypeAlias = Union[int, str]


@final
@dataclass
class Callback(Data):
    event_code: EventCode

    function: Callable[..., Any] = field(repr=False)

    location: "Location"

    parent_name: FileName
    parent_type: Literal["file"]

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

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return False


##############################################################################
# Modules and Contexts
##############################################################################

ModuleName: TypeAlias = str


@final
@dataclass_json
@dataclass
class Module(Data):
    index: int
    description: Optional[str]
    location: "Location"

    parent_name: FileName
    parent_type: Literal["file"]

    @property
    @final
    @override
    def name(self) -> ModuleName:
        return f"{self.parent_name}.module.{self.index}"

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


ContextName: TypeAlias = str


@final
@dataclass_json
@dataclass
class Context(Data):
    matches: list[Match]

    index: int
    description: Optional[str]
    location: "Location"

    parent_name: FileName
    parent_type: Literal["file"]

    @property
    @final
    @override
    def name(self) -> ContextName:
        return f"{self.parent_name}.context.{self.index}"

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

CommandName: TypeAlias = str


@final
@dataclass_json
@dataclass
class Command(Data):
    rule: Rule
    script: Script

    index: int
    description: Optional[str]
    location: "Location"

    parent_name: ContextName
    parent_type: Literal["context"] = "context"

    @property
    def name(self) -> CommandName:
        return f"{self.parent_name}.command.{self.index}"

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

ActionName: TypeAlias = str


@final
@dataclass_json
@dataclass
class Action(Data):
    function_name: Optional[FunctionName]
    function_type_hints: Optional[dict[str, type]]

    name: ActionName
    description: Optional[str]
    location: Union[Literal["builtin"], "Location"]

    parent_name: Union[ModuleName, ContextName]
    parent_type: Literal["module", "context"]

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


CaptureName: TypeAlias = str


@final
@dataclass_json
@dataclass
class Capture(Data):
    rule: Rule
    function_name: Optional[FunctionName]
    function_type_hints: Optional[dict[str, type]]

    name: CaptureName
    description: Optional[str]
    location: Union[Literal["builtin"], "Location"]

    parent_name: Union[ModuleName, ContextName]
    parent_type: Literal["module", "context"]

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


ListName: TypeAlias = str

ListValue: TypeAlias = Union[
    Mapping[str, Any],
    Iterable[str],
]


@final
@dataclass_json
@dataclass
class List(Data):
    value: Optional[ListValue]
    value_type_hint: Optional[type]

    name: ListName
    description: Optional[str]
    location: Union[Literal["builtin"], "Location"]

    parent_name: Union[ModuleName, ContextName]
    parent_type: Literal["module", "context"]

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


SettingName: TypeAlias = str

SettingValue: TypeAlias = Union[Any, Expression]


@final
@dataclass_json
@dataclass
class Setting(Data):
    value: Optional[SettingValue]
    value_type_hint: Optional[type]

    name: SettingName
    description: Optional[str]
    location: Union[Literal["builtin"], "Location"]

    parent_name: Union[ModuleName, ContextName]
    parent_type: Literal["module", "context"]

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


ModeName: TypeAlias = str


@final
@dataclass_json
@dataclass
class Mode(Data):
    name: ModeName
    description: Optional[str]
    location: Union[Literal["builtin"], "Location"]

    parent_name: ModuleName
    parent_type: Literal["module"] = "module"

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


TagName: TypeAlias = str


@final
@dataclass_json
@dataclass
class Tag(Data):
    name: TagName
    description: Optional[str]
    location: Union[Literal["builtin"], "Location"]

    parent_name: ModuleName
    parent_type: Literal["module"] = "module"

    @classmethod
    @final
    @override
    def is_serialisable(cls) -> bool:
        return True


##############################################################################
# Type Variables
##############################################################################

SimpleData: TypeAlias = Union[
    Package,
    File,
    Function,
    Module,
    Context,
    Command,
    Mode,
    Tag,
]


def is_simple(cls: type[Data]) -> TypeGuard[type[SimpleData]]:
    return issubclass(
        cls,
        (
            Package,
            File,
            Function,
            Module,
            Context,
            Command,
            Mode,
            Tag,
        ),
    )


SimpleDataVar = TypeVar(
    "SimpleDataVar",
    bound=SimpleData,
)


GroupData: TypeAlias = Union[
    Action,
    Capture,
    List,
    Setting,
]


def is_group(cls: type[Data]) -> TypeGuard[type[GroupData]]:
    return issubclass(
        cls,
        (
            Action,
            Capture,
            List,
            Setting,
        ),
    )


GroupDataVar = TypeVar(
    "GroupDataVar",
    bound=GroupData,
)


##############################################################################
# Groups
##############################################################################


class Group(Generic[GroupDataVar]):
    declarations: list[GroupDataVar] = field(default_factory=list)
    overrides: list[GroupDataVar] = field(default_factory=list)

    def append(self, value: GroupDataVar) -> None:
        if value.parent_type == "module":
            self.declarations.append(value)
        else:
            self.overrides.append(value)


##############################################################################
# Exceptions
##############################################################################


@dataclass(frozen=True)
class DuplicateData(Exception):
    """Raised when an entry is defined in multiple modules."""

    entry1: Data
    entry2: Data

    def __str__(self) -> str:
        class_name1 = self.entry1.__class__.__name__
        class_name2 = self.entry2.__class__.__name__
        if class_name1 != class_name2:
            _LOGGER.warning(
                f"DuplicateData exception with types {class_name1} and {class_name2}"
            )
        entry_name1 = self.entry1.name
        entry_name2 = self.entry2.name
        if class_name1 != class_name2:
            _LOGGER.warning(
                f"DuplicateData exception with names {entry_name1} and {entry_name2}"
            )
        return "\n".join(
            [
                f"{class_name1} '{entry_name1}' is declared twice:",
                f"- {self.entry1.location}",
                f"- {self.entry2.location}",
            ]
        )


##############################################################################
# Source Locations
##############################################################################


@final
@dataclass_json
@dataclass
class Location:
    path: Path
    start_position: Optional[Point] = None
    end_position: Optional[Point] = None

    def __str__(self) -> str:
        if self.start_position is not None:
            return (
                f"{self.path}:{self.start_position.line}:{self.start_position.column}"
            )
        return f"{self.path}"

    @staticmethod
    def from_ast(path: Path, node: Node) -> "Location":
        return Location(
            path=path,
            start_position=node.start_position,
            end_position=node.end_position,
        )

    @staticmethod
    def from_function(function: Callable[..., Any]) -> "Location":
        code = function.__code__
        path = Path(code.co_filename)
        start_position = Point(code.co_firstlineno, 0)
        return Location(path=path, start_position=start_position)

    @staticmethod
    def from_path(path: Path) -> "Location":
        return Location(path=path)
