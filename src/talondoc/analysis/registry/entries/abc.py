from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional, Sequence, Union

import editdistance
from tree_sitter_talon import Node as Node
from tree_sitter_talon import Point as Point
from typing_extensions import Literal, TypeVar, final

from ...._util.logging import getLogger

_LOGGER = getLogger(__name__)


if TYPE_CHECKING:
    from . import Context, File, Module, Package
else:
    Package = "SimpleData"
    File = "SimpleData"
    Module = "SimpleData"
    Context = "SimpleData"


##############################################################################
# Source Locations
##############################################################################


@final
@dataclass
class Location:
    path: Path
    start_line: Optional[int] = None
    start_column: Optional[int] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None

    @staticmethod
    def _str_from_point(line: Optional[int], column: Optional[int]) -> Optional[str]:
        if line is not None:
            if column is not None:
                return f"{line}"
            else:
                return f"{line}:{column}"
        else:
            return None

    def __str__(self) -> str:
        start_position = Location._str_from_point(self.start_line, self.start_column)
        if start_position:
            end_position = Location._str_from_point(self.end_line, self.end_column)
            if end_position:
                return f"{self.path}:{start_position}-{end_position}"
            else:
                return f"{self.path}:{start_position}"
        else:
            return f"{self.path}"

    @staticmethod
    def from_ast(path: Path, node: Node) -> "Location":
        return Location(
            path=path,
            start_line=node.start_position.line,
            start_column=node.start_position.column,
            end_line=node.end_position.line,
            end_column=node.end_position.column,
        )

    @staticmethod
    def from_function(function: Callable[..., Any]) -> "Location":
        assert callable(function), f"Location.from_function received {repr(function)}"
        path = Path(function.__code__.co_filename)
        return Location(path=path, start_line=function.__code__.co_firstlineno)

    @staticmethod
    def from_path(path: Path) -> "Location":
        return Location(path=path)


##############################################################################
# Abstact Data
##############################################################################


@dataclass
class Data:
    name: str
    description: Optional[str]
    location: Union[Literal["builtin"], "Location"]
    parent_name: Optional[str]
    parent_type: Optional[Union[type[Package], type[File], type[Module], type[Context]]]
    serialisable: bool


DataVar = TypeVar("DataVar", bound=Data)


##############################################################################
# Simple Data
##############################################################################


class SimpleData(Data):
    pass


SimpleDataVar = TypeVar(
    "SimpleDataVar",
    bound=SimpleData,
)


##############################################################################
# Grouped Data
##############################################################################


@dataclass
class GroupData(Data):
    parent_name: str
    parent_type: Union[type[Module], type[Context]]


GroupDataVar = TypeVar(
    "GroupDataVar",
    bound=GroupData,
)


##############################################################################
# Grouped Data with Function
##############################################################################


class GroupDataHasFunction(GroupData):
    function_name: Optional[str]
    function_type_hints: Optional[Mapping[str, type]]


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

    referenced_by: Optional[Data]
    known_references: Optional[Sequence[str]]

    def __str__(self) -> str:
        buffer = []

        # If referenced_by is set, include it:
        if self.referenced_by is not None:
            referenced_by_type_name = self.referenced_by.__class__.__name__.lower()
            buffer.append(
                f"{referenced_by_type_name} {self.referenced_by.name} references"
            )

        # Include unknown reference:
        ref_type_name = self.ref_type.__name__.lower()
        buffer.append(f"unknown {ref_type_name} {self.ref_name}")

        # If known_references is set, include the closest matching subset:
        if self.known_references is not None:

            def _distance(known_ref_name: str) -> int:
                return editdistance.eval(self.ref_name, known_ref_name)

            closest_known_references = sorted(self.known_references, key=_distance)[:10]
            buffer.append(f"(Did you mean {', '.join(closest_known_references)})")

        return " ".join(buffer)
