from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Union, cast

from dataclasses_json import dataclass_json
from tree_sitter_talon import Node as Node
from tree_sitter_talon import Point as Point
from typing_extensions import Final, Literal, TypeAlias, TypeVar, final

from ...util.logging import getLogger

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
ListValue: TypeAlias = Union[Dict[str, Any], List[str]]
SettingValue: TypeAlias = Any


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
# Simple Data
##############################################################################


class SimpleData(Data, metaclass=ABCMeta):
    pass


SimpleDataVar = TypeVar(
    "SimpleDataVar",
    bound=SimpleData,
)


##############################################################################
# Grouped Data
##############################################################################


class GroupData(Data, metaclass=ABCMeta):
    @property
    @abstractmethod
    def parent_name(self) -> str:
        ...

    @property
    @abstractmethod
    def parent_type(self) -> Literal["module", "context"]:
        ...


GroupDataVar = TypeVar(
    "GroupDataVar",
    bound=GroupData,
)


##############################################################################
# Grouped Data with Function
##############################################################################


class GroupDataHasFunction(GroupData, metaclass=ABCMeta):
    @property
    @abstractmethod
    def function_name(self) -> Optional[FunctionName]:
        ...

    @property
    @abstractmethod
    def function_type_hints(self) -> Optional[Mapping[str, type]]:
        ...


GroupDataHasFunctionVar = TypeVar(
    "GroupDataHasFunctionVar",
    bound=GroupDataHasFunction,
)

##############################################################################
# Exceptions
##############################################################################


@dataclass(frozen=True)
class DuplicateData(Exception):
    """Raised when an entry is defined in multiple modules."""

    data1: Data
    data2: Data

    def __str__(self) -> str:
        cls_name1 = self.data1.__class__.__name__
        cls_name2 = self.data2.__class__.__name__
        if cls_name1 != cls_name2:
            _LOGGER.warning(
                f"DuplicateData exception with types {cls_name1} and {cls_name2}"
            )
        data_name1 = self.data1.name
        data_name2 = self.data2.name
        if cls_name1 != cls_name2:
            _LOGGER.warning(
                f"DuplicateData exception with names {data_name1} and {data_name2}"
            )
        return "\n".join(
            [
                f"{cls_name1} '{data_name1}' is declared twice:",
                f"- {self.data1.location}",
                f"- {self.data2.location}",
            ]
        )


@dataclass(frozen=True)
class UnknownReference(Exception):
    """Raised when an entry is defined in multiple modules."""

    ref_type: type[Data]
    ref_name: str

    data: Optional[Data]

    def __str__(self) -> str:
        buffer = []
        if self.data is not None:
            buffer.append(f"{self.data.__class__.__name__} references")
        buffer.append(f"unknown {self.ref_type.__name__} '{self.ref_name}'")
        return " ".join(buffer)
