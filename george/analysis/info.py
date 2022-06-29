from dataclasses import dataclass, field
from dataclasses_json import dataclass_json, config
from enum import Enum
from typing import Mapping, Optional, Sequence, Set
import ast

TalonSort = Enum(
    "TalonSort",
    [
        "Action",
        "List",
        "Capture",
        "Tag",
        "Setting",
    ],
)


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
    name: str
    sort: TalonSort = field(
        metadata=config(encoder=str, decoder=lambda sort: TalonSort[sort])
    )
    is_override: bool
    desc: Optional[str] = None
    node: Optional[ast.AST] = field(
        default=None,
        metadata=config(
            encoder=lambda node: Source.from_ast(node).to_dict(),
            decoder=lambda json: Source.from_dict(json).to_ast(),
        ),
    )


@dataclass_json
@dataclass(frozen=True)
class PythonInfo:
    path: str
    declarations: Mapping[TalonSort, Mapping[str, TalonDecl]]
    overrides: Mapping[TalonSort, Mapping[str, Sequence[TalonDecl]]]
    uses: Mapping[TalonSort, Set[str]]
