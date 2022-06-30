from dataclasses import dataclass
from dataclasses_json import dataclass_json, DataClassJsonMixin
from dataclasses_json.core import Json
from enum import Enum
from typing import Mapping, Optional, Set, TypeVar
import ast

A = TypeVar("A", bound="DataClassJsonMixin")

TalonDeclName = str
TalonSortName = str


class TalonSort(Enum):
    Action = 1
    Capture = 2
    List = 3
    Setting = 4
    Tag = 5

    @staticmethod
    def parse(sort: str) -> "TalonSort":
        return TalonSort[sort]


@dataclass_json
@dataclass(frozen=True)
class Position:
    line: int
    column: int

    @staticmethod
    def from_ast(node: ast.AST):
        return Position(line=node.lineno, column=node.col_offset)


@dataclass_json
@dataclass(frozen=True)
class Source:
    source: str
    position: Position

    @staticmethod
    def from_ast(node: ast.AST) -> "Source":
        source = ast.unparse(node)
        position = Position.from_ast(node)
        return Source(source=source, position=position)

    def to_ast(self) -> ast.AST:
        node = ast.parse(self.source)
        node.lineno = self.position.start.line
        node.col_offset = self.position.start.column
        return node


@dataclass_json
@dataclass(frozen=True)
class TalonDecl:
    name: TalonDeclName
    sort: TalonSortName
    is_override: bool
    source: Source
    desc: Optional[str] = None


@dataclass_json
@dataclass(frozen=True)
class PythonInfo:
    path: str
    declarations: Mapping[TalonSortName, Mapping[TalonDeclName, TalonDecl]]
    overrides: Mapping[TalonSortName, Mapping[TalonDeclName, Set[TalonDecl]]]
    uses: Mapping[TalonSortName, Set[TalonDeclName]]
