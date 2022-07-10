from dataclasses import dataclass, field
from logging import warn
from types import CodeType
import types
from dataclasses_json import config, dataclass_json
from dataclasses_json.core import Json
from enum import Enum
from typing import Callable, Generator, Optional, Union
import george.talon.tree_sitter as talon
import marshal
import base64

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
    Mode = 7


@dataclass_json
@dataclass
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
    def from_code(node: CodeType) -> "Position":
        return Position(line=node.co_firstlineno)


@dataclass_json
@dataclass
class Source:
    text: Optional[str]
    position: Position

    @staticmethod
    def from_ast(node: ast.AST) -> "Source":
        return Source(text=ast.unparse(node), position=Position.from_ast(node))

    @staticmethod
    def from_tree_sitter(node: ts.Node) -> "Source":
        return Source(text=node.text.decode(), position=Position.from_tree_sitter(node))

    @staticmethod
    def from_code(node: CodeType) -> "Source":
        return Source(text=None, position=Position.from_code(node))


@dataclass_json
@dataclass
class TalonRule:
    source: Source
    rule: Optional[talon.types.Rule] = None

    @staticmethod
    def parse(text: str, position: Optional[Position] = None) -> Optional["TalonRule"]:
        position = position or Position(line=0, column=0)
        tree = talon.parse(bytes(f"-\n{text}: skip()\n", "utf-8"))
        rule_query = talon.language.query("(rule) @rule")
        captures = rule_query.captures(tree.root_node)
        if captures:
            for rule, anchor in captures:
                assert anchor == "rule"
                return TalonRule(
                    source=Source(text=text, position=position),
                    rule=talon.types.from_tree_sitter(rule),
                )


@dataclass_json
@dataclass
class TalonDecl:
    name: TalonDeclName
    sort_name: TalonSortName
    matches: Union[bool, talon.types.Context] = False
    desc: Optional[str] = None
    source: Optional[Source] = None
    file_path: Optional[str] = None


class Function:
    @staticmethod
    def encode(action_impl: Optional[Callable]) -> Optional[Json]:
        if action_impl:
            name = action_impl.__code__.co_name
            code = base64.b64encode(marshal.dumps(action_impl.__code__)).decode("utf-8")
            return {
                "name": name,
                "code": code,
            }

    @staticmethod
    def decode(data: Optional[Json]) -> Optional[Callable]:
        if data:
            name = data["name"]
            code = marshal.loads(base64.b64decode(bytes(data["code"], "utf-8")))
            return types.FunctionType(code, globals(), name)


@dataclass_json
@dataclass
class ActionDecl(TalonDecl):
    sort_name: TalonSortName = TalonSort.Action.name
    impl: Optional[Callable] = field(
        default=None,
        metadata=config(encoder=Function.encode, decoder=Function.decode),
    )

    def __post_init__(self, **kwargs):
        if self.impl:
            if not self.desc:
                self.desc = self.impl.__doc__
            if not self.source:
                self.source = Source.from_code(self.impl.__code__)


@dataclass_json
@dataclass
class CaptureDecl(TalonDecl):
    sort_name: TalonSortName = TalonSort.Capture.name
    rule: Optional[TalonRule] = None
    impl: Optional[Callable] = field(
        default=None,
        metadata=config(encoder=Function.encode, decoder=Function.decode),
    )

    def __post_init__(self, **kwargs):
        if self.impl:
            if not self.desc:
                self.desc = self.impl.__doc__
            if not self.source:
                self.source = Source.from_code(self.impl.__code__)


@dataclass_json
@dataclass
class ListDecl(TalonDecl):
    sort_name: TalonSortName = TalonSort.List.name
    contents: Optional[dict[str, any]] = None


@dataclass_json
@dataclass
class TagDecl(TalonDecl):
    sort_name: TalonSortName = TalonSort.Tag.name


@dataclass_json
@dataclass
class ModeDecl(TalonDecl):
    sort_name: TalonSortName = TalonSort.Mode.name


@dataclass_json
@dataclass
class TalonScript:
    text: str
    source: Source
    desc: Optional[str] = None


@dataclass_json
@dataclass
class TalonCommand:
    rule: TalonRule
    script: TalonScript


@dataclass_json
@dataclass
class TalonFileInfo:
    file_path: str
    commands: list[TalonCommand]
    uses: dict[TalonSortName, list[TalonDeclName]]


@dataclass_json
@dataclass
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
@dataclass
class PythonFileInfo:
    file_path: str
    declarations: dict[TalonSortName, dict[TalonDeclName, TalonDecl]] = field(
        default_factory=dict
    )
    overrides: dict[TalonSortName, dict[TalonDeclName, list[TalonDecl]]] = field(
        default_factory=dict
    )
    uses: dict[TalonSortName, list[TalonDeclName]] = field(default_factory=dict)

    def add_declaration(self, decl: "TalonDecl"):
        if isinstance(decl.sort_name, TalonSort):
            warn(f"TalonDecl with TalonSort: {decl}")
        if decl.matches == False:
            if not decl.sort_name in self.declarations:
                self.declarations[decl.sort_name] = {}
            self.declarations[decl.sort_name][decl.name] = decl
        else:
            if not decl.sort_name in self.overrides:
                self.overrides[decl.sort_name] = {}
            if not decl.name in self.overrides[decl.sort_name]:
                self.overrides[decl.sort_name][decl.name] = list()
            self.overrides[decl.sort_name][decl.name].append(decl)

    def add_use(self, sort_name: TalonSortName, name: TalonDeclName):
        if isinstance(sort_name, TalonSort):
            warn(f"add_use called with TalonSort: {sort_name}")
        if not sort_name in self.uses:
            self.uses[sort_name] = list()
        self.uses[sort_name].append(name)


@dataclass_json
@dataclass
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
