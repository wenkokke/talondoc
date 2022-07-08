from collections import defaultdict
from dataclasses import dataclass, field
from logging import warn
from types import CodeType, NoneType
from dataclasses_json import config, dataclass_json
from enum import Enum
from typing import Any, Callable, Generator, Optional, Union

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
    column: Optional[int] = None

    @staticmethod
    def from_ast(node: ast.AST):
        return Position(line=node.lineno, column=node.col_offset)

    @staticmethod
    def from_tree_sitter(node: ts.Node) -> "Position":
        line, column = node.start_point
        return Position(line=line, column=column)

    @staticmethod
    def from_code_type(node: CodeType) -> "Position":
        return Position(line=node.co_firstlineno)


@dataclass_json
@dataclass(frozen=True)
class Source:
    source: Optional[str]
    position: Position

    @staticmethod
    def from_ast(node: ast.AST) -> "Source":
        return Source(source=ast.unparse(node), position=Position.from_ast(node))

    @staticmethod
    def from_tree_sitter(node: ts.Node) -> "Source":
        return Source(
            source=node.text.decode(), position=Position.from_tree_sitter(node)
        )

    @staticmethod
    def from_code_type(node: CodeType) -> "Source":
        return Source(source=None, position=Position.from_code_type(node))


ValueType = Union[Callable, dict[str, any], str, None]


def value_encoder(value: ValueType):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return value
    return None


@dataclass_json
@dataclass(frozen=True)
class TalonDecl:
    name: TalonDeclName
    sort_name: TalonSortName
    file_path: str
    is_override: bool
    source: Source
    desc: Optional[str] = None
    value: ValueType = field(default=None, metadata=config(encoder=value_encoder))


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
    declarations: dict[TalonSortName, dict[TalonDeclName, TalonDecl]] = field(
        default_factory=dict
    )
    overrides: dict[TalonSortName, dict[TalonDeclName, set[TalonDecl]]] = field(
        default_factory=dict
    )
    uses: dict[TalonSortName, set[TalonDeclName]] = field(default_factory=dict)

    def add_declaration(self, decl: "TalonDecl"):
        if isinstance(decl.sort_name, TalonSort):
            warn(f"TalonDecl with TalonSort: {decl}")
        if decl.is_override:
            if not decl.sort_name in self.overrides:
                self.overrides[decl.sort_name] = {}
            if not decl.name in self.overrides[decl.sort_name]:
                self.overrides[decl.sort_name][decl.name] = set()
            self.overrides[decl.sort_name][decl.name].add(decl)
        else:
            if not decl.sort_name in self.declarations:
                self.declarations[decl.sort_name] = {}
            self.declarations[decl.sort_name][decl.name] = decl

    def add_use(self, sort_name: TalonSortName, name: TalonDeclName):
        if isinstance(sort_name, TalonSort):
            warn(f"add_use called with TalonSort: {sort_name}")
        if not sort_name in self.uses:
            self.uses[sort_name] = set()
        self.uses[sort_name].add(name)


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
