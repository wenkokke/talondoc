from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import inspect
from logging import warn
import operator
from pathlib import Path
from types import CodeType
import types
from dataclasses_json import config, dataclass_json
from dataclasses_json.core import Json
from enum import Enum
from typing import Callable, Generator, Optional, Sequence, Type, TypeVar, Union
import george.talon.tree_sitter as talon
import marshal
import base64

import ast
import tree_sitter as ts

TalonName = str
TalonSortName = str


class TalonSort(Enum):
    Command = 1
    Action = 2
    Capture = 3
    List = 4
    Setting = 5
    Tag = 6
    Mode = 7


# Merging Helpers


def dict_merged_with(dict1: dict, dict2: dict, value_merged_with=operator.__or__):
    return {
        key: value_merged_with(dict1.get(key, None), dict2.get(key, None))
        for key in dict1.keys() | dict2.keys()
    }


def list_merged(list1: Optional[list], list2: Optional[list]) -> list:
    if list1 and list2:
        return list1 + list2
    elif list1:
        return list1
    else:
        return list2


# Encode/Decode Helpers


class Encode:
    @staticmethod
    def function(func: Optional[Callable]) -> Optional[Json]:
        if func:
            name = func.__code__.co_name
            code = base64.b64encode(marshal.dumps(func.__code__)).decode("utf-8")
            return {
                "name": name,
                "code": code,
            }

    @staticmethod
    def type(type: Optional[type]) -> Optional[Json]:
        if type:
            if inspect.isfunction(type):
                return Encode.function(type)
            if type in [str, int]:
                return type.__name__
            return None


class Decode:
    @staticmethod
    def function(data: Optional[Json]) -> Optional[Callable]:
        if data:
            name = data["name"]
            code = marshal.loads(base64.b64decode(bytes(data["code"], "utf-8")))
            return types.FunctionType(code, globals(), name)

    @staticmethod
    def type(data: Optional[Json]) -> Optional[type]:
        if data:
            if isinstance(data, dict) and "name" in data and "code" in data:
                return Decode.function(data)
            if isinstance(data, str):
                return {
                    "str": str,
                    "int": int,
                }[data]
            return None


# Source Information


@dataclass_json
@dataclass
class Position:
    line: int
    column: Optional[int] = None


@dataclass_json
@dataclass
class Source:
    file_path: str
    text: Optional[str] = None
    start: Optional[Position] = None
    end: Optional[Position] = None

    @staticmethod
    def from_ast(file_path: Union[str, Path], node: ast.AST) -> "Source":
        if isinstance(file_path, Path):
            file_path = str(file_path)
        text = ast.unparse(node)
        start = Position(line=node.lineno, column=node.col_offset)
        if node.end_lineno is None:
            end = None
        else:
            end = Position(line=node.end_lineno, column=node.end_col_offset)
        return Source(file_path, text=text, start=start, end=end)

    @staticmethod
    def from_tree_sitter(file_path: Union[str, Path], node: ts.Node) -> "Source":
        if isinstance(file_path, Path):
            file_path = str(file_path)
        text = node.text.decode("utf-8")
        start = Position(*node.start_point)
        end = Position(*node.end_point)
        return Source(file_path, text=text, start=start, end=end)

    @staticmethod
    def from_code(node: CodeType) -> "Source":
        file_path = node.co_filename
        start = Position(line=node.co_firstlineno)
        return Source(file_path, text=None, start=start)


# Context Matches


@dataclass_json
@dataclass
class TalonMatches(ABC):
    @property
    def is_override(self) -> bool:
        raise NotImplementedError


@dataclass_json
@dataclass
class TalonModule(TalonMatches):
    @property
    def is_override(self) -> bool:
        return False


TalonMatchDecl = Union[
    talon.types.Or, talon.types.And, talon.types.Not, talon.types.Match
]


@dataclass_json
@dataclass
class TalonContext(TalonMatches):
    @property
    def is_override(self) -> bool:
        return True

    matches: Optional[list[TalonMatchDecl]] = None
    tags: list[TalonName] = field(default_factory=list)

    @staticmethod
    def parse(text: str) -> Optional[list[TalonMatchDecl]]:
        tree = talon.parse(bytes(f"{text}\n-\n", "utf-8"), has_header=True)
        context_query = talon.language.query("(context) @context")
        captures = context_query.captures(tree.root_node)
        if captures:
            for context, anchor in captures:
                assert anchor == "context"
                return talon.types.from_tree_sitter(context).children
        return None


# Commands


@dataclass_json
@dataclass
class TalonRule:
    rule: Optional[talon.types.Rule] = None
    source: Optional[Source] = None

    @staticmethod
    def parse(text: str) -> Optional["TalonRule"]:
        tree = talon.parse(bytes(f"-\n{text}: skip()\n", "utf-8"), has_header=True)
        rule_query = talon.language.query("(rule) @rule")
        captures = rule_query.captures(tree.root_node)
        if captures:
            for rule, anchor in captures:
                assert anchor == "rule"
                return TalonRule(
                    rule=talon.types.from_tree_sitter(rule),
                )
        return None


@dataclass_json
@dataclass
class TalonScript:
    source: Source
    desc: Optional[str] = None


@dataclass_json
@dataclass
class TalonCommand:
    rule: TalonRule
    script: TalonScript


# Declarations


@dataclass_json
@dataclass
class TalonDecl(ABC):
    name: TalonName
    matches: TalonMatches
    source: Source
    desc: Optional[str] = None

    @property
    @abstractmethod
    def sort(self) -> TalonSort:
        """
        The sort of the declaration.
        """


@dataclass_json
@dataclass
class TalonActionDecl(TalonDecl):
    source: Source = None
    impl: Optional[Callable] = field(
        default=None,
        metadata=config(encoder=Encode.function, decoder=Decode.function),
    )

    def __post_init__(self, **kwargs):
        if self.impl and not self.source:
            self.source = Source.from_code(self.impl.__code__)
        if self.impl and not self.desc:
            self.desc = self.impl.__doc__

    @property
    def sort(self):
        return TalonSort.Action


@dataclass_json
@dataclass
class TalonCaptureDecl(TalonDecl):
    source: Source = None
    rule: Optional[TalonRule] = None
    impl: Optional[Callable] = field(
        default=None,
        metadata=config(encoder=Encode.type, decoder=Decode.type),
    )

    def __post_init__(self, **kwargs):
        if self.impl and not self.source:
            self.source = Source.from_code(self.impl.__code__)
        if self.impl and not self.desc:
            self.desc = self.impl.__doc__

    @property
    def sort(self):
        return TalonSort.Capture


ListValue = Union[dict[str, str], Sequence[str]]


@dataclass_json
@dataclass
class TalonListDecl(TalonDecl):
    list: Optional[ListValue] = None

    @property
    def sort(self):
        return TalonSort.List


@dataclass_json
@dataclass
class TalonTagDecl(TalonDecl):
    @property
    def sort(self):
        return TalonSort.Tag


@dataclass_json
@dataclass
class TalonModeDecl(TalonDecl):
    @property
    def sort(self):
        return TalonSort.Mode


SettingValue = any


@dataclass_json
@dataclass
class TalonSettingDecl(TalonDecl):
    type: Optional[Type] = field(
        default=None,
        metadata=config(encoder=Encode.type, decoder=Decode.type),
    )
    default: Optional[any] = None

    @property
    def sort(self):
        return TalonSort.Setting


DeclType = TypeVar("DeclType", bound=TalonDecl)


@dataclass_json
@dataclass
class TalonDecls(tuple[DeclType, list[DeclType]]):
    sort: TalonSort
    declaration: DeclType = None
    overrides: list[DeclType] = field(default_factory=list)

    def merged_with(self, other: "TalonDecls") -> "TalonDecls":
        if other:
            assert self.sort == other.sort
            return self
        else:
            return self

    def __or__(self, other: "TalonDecls") -> "TalonDecls":
        return self.merged_with(other)

    def __ror__(self, other: "TalonDecls") -> "TalonDecls":
        return self.merged_with(other)


# Talon Files


@dataclass_json
@dataclass
class TalonFileInfo:
    file_path: str
    package_root: str
    commands: list[TalonCommand]
    uses: dict[TalonSortName, list[TalonName]]


@dataclass_json
@dataclass
class TalonPackageInfo:
    package_root: str
    file_infos: dict[str, TalonFileInfo]


# Python Files


@dataclass_json
@dataclass
class PythonFileInfo:
    file_path: str
    package_root: str
    actions: dict[TalonName, TalonDecls[TalonActionDecl]] = field(default_factory=dict)
    captures: dict[TalonName, TalonDecls[TalonCaptureDecl]] = field(
        default_factory=dict
    )
    lists: dict[TalonName, TalonDecls[TalonListDecl]] = field(default_factory=dict)
    settings: dict[TalonName, TalonDecls[TalonSettingDecl]] = field(
        default_factory=dict
    )
    tags: dict[TalonName, TalonDecls[TalonTagDecl]] = field(default_factory=dict)
    modes: dict[TalonName, TalonDecls[TalonModeDecl]] = field(default_factory=dict)
    uses: dict[TalonSortName, list[TalonName]] = field(default_factory=dict)

    def _get_declaration_dict(self, sort: str):
        return {
            TalonSort.Action: self.actions,
            TalonSort.Capture: self.captures,
            TalonSort.List: self.lists,
            TalonSort.Setting: self.settings,
            TalonSort.Tag: self.tags,
            TalonSort.Mode: self.modes,
        }[sort]

    def add_declaration(self, decl: "TalonDecl"):
        declaration_dict = self._get_declaration_dict(decl.sort)
        if decl.name in declaration_dict:
            decls = declaration_dict[decl.name]
        else:
            decls = declaration_dict[decl.name] = TalonDecls(sort=decl.sort)
        if decl.matches.is_override:
            decls.overrides.append(decl)
        else:
            decls.declaration = decl

    def add_use(self, sort: TalonSort, name: TalonName):
        if not sort.name in self.uses:
            self.uses[sort.name] = list()
        self.uses[sort.name].append(name)

    def merged_with(self, other: Optional["PythonFileInfo"]) -> "PythonFileInfo":
        if other:
            assert self.file_path == other.file_path
            assert self.package_root == other.package_root
            return PythonFileInfo(
                file_path=self.file_path,
                package_root=self.package_root,
                actions=dict_merged_with(self.actions, other.actions),
                captures=dict_merged_with(self.captures, other.captures),
                lists=dict_merged_with(self.lists, other.lists),
                settings=dict_merged_with(self.settings, other.settings),
                tags=dict_merged_with(self.tags, other.tags),
                modes=dict_merged_with(self.modes, other.modes),
                uses=dict_merged_with(
                    self.uses, other.uses, value_merged_with=list_merged
                ),
            )
        else:
            return self

    def __or__(self, other: Optional["PythonFileInfo"]) -> "PythonFileInfo":
        return self.merged_with(other)

    def __ror__(self, other: Optional["PythonFileInfo"]) -> "PythonFileInfo":
        return self.merged_with(other)


@dataclass_json
@dataclass
class PythonPackageInfo:
    package_root: str
    file_infos: dict[str, PythonFileInfo] = field(default_factory=dict)

    def get_action_declaration(self, name: TalonName) -> Optional[TalonActionDecl]:
        for file_info in self.file_infos.values():
            try:
                if name in file_info.actions:
                    return file_info.actions[name].declaration
            except AttributeError:
                print(type(file_info))
                exit()
        return None

    def merged_with(self, other: Optional["PythonPackageInfo"]) -> "PythonPackageInfo":
        if other:
            assert self.package_root == other.package_root
            return PythonPackageInfo(
                package_root=self.package_root,
                file_infos=dict_merged_with(self.file_infos, other.file_infos),
            )
        else:
            return self

    def __or__(self, other: Optional["PythonPackageInfo"]) -> "PythonPackageInfo":
        return self.merged_with(other)

    def __ror__(self, other: Optional["PythonPackageInfo"]) -> "PythonPackageInfo":
        return self.merged_with(other)
