from dataclasses import dataclass, field
from dataclasses_json import dataclass_json
from enum import Enum
from typing import Generator, Optional

import ast
import tree_sitter as ts

TalonDeclName = str
TalonSortName = str


class TalonSort(Enum):
    Command = 1
    Action = 2
    Capture = 3
    List = 4
    Setting = 5
    Tag = 6


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

    @staticmethod
    def from_tree_sitter(node: ts.Node) -> "Source":
        line, column = node.start_point
        return Source(
            source=node.text.decode(), position=Position(line=line, column=column)
        )


@dataclass_json
@dataclass(frozen=True)
class TalonDecl:
    name: TalonDeclName
    sort_name: TalonSortName
    file_path: str
    is_override: bool
    source: Source
    desc: Optional[str] = None


@dataclass_json
@dataclass(frozen=True)
class TalonRule:
    text: str
    source: Source


@dataclass_json
@dataclass(frozen=True)
class TalonScript:
    text: str
    source: Source
    desc: Optional[str] = None


@dataclass_json
@dataclass(frozen=True)
class TalonCommand:
    rule: TalonRule
    script: TalonScript


@dataclass_json
@dataclass(frozen=True)
class TalonFileInfo:
    file_path: str
    commands: list[TalonCommand]
    uses: dict[TalonSortName, set[TalonDeclName]]


@dataclass_json
@dataclass(frozen=True)
class TalonPackageInfo:
    package_root: str
    file_infos: dict[str, TalonFileInfo]

    def uses(
        self, sort: TalonSortName, name: TalonDeclName
    ) -> Generator[str, None, None]:
        for file_path, file_info in self.file_infos.items():
            if sort in file_info.overrides and name in file_info.uses[sort]:
                yield file_path


@dataclass_json
@dataclass(frozen=True)
class PythonFileInfo:
    file_path: str
    declarations: dict[TalonSortName, dict[TalonDeclName, TalonDecl]]
    overrides: dict[TalonSortName, dict[TalonDeclName, set[TalonDecl]]]
    uses: dict[TalonSortName, set[TalonDeclName]]


@dataclass_json
@dataclass(frozen=True)
class PythonPackageInfo:
    package_root: str
    file_infos: dict[str, PythonFileInfo] = field(default_factory=dict)

    def declaration(
        self, sort: TalonSortName, name: TalonDeclName
    ) -> Optional[TalonDecl]:
        for _, file_info in self.file_infos.items():
            if sort in file_info.declarations and name in file_info.declarations[sort]:
                return file_info.declarations[sort][name]

    def overrides(
        self, sort: TalonSortName, name: TalonDeclName
    ) -> Generator[TalonDecl, None, None]:
        for _, file_info in self.file_infos.items():
            if sort in file_info.overrides and name in file_info.overrides[sort]:
                for override in file_info.overrides[sort][name]:
                    yield override

    def uses(
        self, sort: TalonSortName, name: TalonDeclName
    ) -> Generator[str, None, None]:
        for file_path, file_info in self.file_infos.items():
            if sort in file_info.overrides and name in file_info.uses[sort]:
                yield file_path
