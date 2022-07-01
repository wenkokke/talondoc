from dataclasses import dataclass, field
from dataclasses_json import config, dataclass_json
from enum import Enum
from typing import Optional
import ast

TalonDeclName = str
TalonSortName = str


class TalonSort(Enum):
    Action = 1
    Capture = 2
    List = 3
    Setting = 4
    Tag = 5


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
        return Source(source=ast.unparse(node), position=Position.from_ast(node))


@dataclass_json
@dataclass(frozen=True)
class TalonDecl:
    name: TalonDeclName
    sort: TalonSort = field(
        metadata=config(
            encoder=lambda sort: sort.name,
            decoder=lambda name: TalonSort[name]
        )
    )
    is_override: bool
    source: Source
    desc: Optional[str] = None


@dataclass_json
@dataclass(frozen=True)
class PythonInfo:
    path: str
    declarations: dict[TalonSortName, dict[TalonDeclName, TalonDecl]]
    overrides: dict[TalonSortName, dict[TalonDeclName, set[TalonDecl]]]
    uses: dict[TalonSortName, set[TalonDeclName]]

@dataclass_json
@dataclass(frozen=True)
class TalonRule:
    text: str

@dataclass_json
@dataclass(frozen=True)
class TalonScript:
    script: str

@dataclass_json
@dataclass(frozen=True)
class TalonInfo:
    path: str
    commands: dict[TalonRule, TalonScript]
    uses: dict[TalonSortName, set[TalonDeclName]]