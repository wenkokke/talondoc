from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import inspect
from pathlib import Path
from types import CodeType
import types
from dataclasses_json import config, dataclass_json
from dataclasses_json.core import Json
from enum import Enum
from typing import (
    Callable,
    ForwardRef,
    Generic,
    Mapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
)
import marshal
import base64

import ast
import tree_sitter as ts
import tree_sitter_talon as talon

from george.python.analysis import dynamic

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


# Encode/Decode Helpers


def _encode_function(func: Optional[Callable]) -> Optional[Json]:
    if func:
        name = func.__code__.co_name
        code = base64.b64encode(marshal.dumps(func.__code__)).decode("utf-8")
        return {
            "name": name,
            "code": code,
        }


def _decode_function(data: Optional[Json]) -> Optional[Callable]:
    if data:
        name = data["name"]
        code = marshal.loads(base64.b64decode(bytes(data["code"], "utf-8")))
        return types.FunctionType(code, globals(), name)


def _encode_type(type: Optional[type]) -> Optional[Json]:
    if type:
        if inspect.isfunction(type):
            return _encode_function(type)
        if type in [str, int]:
            return type.__name__
        return None


def _decode_type(data: Optional[Json]) -> Optional[type]:
    if data:
        if isinstance(data, dict) and "name" in data and "code" in data:
            return _decode_function(data)
        if isinstance(data, str):
            return {
                "str": str,
                "int": int,
            }[data]
        return None


# Merging Helpers

T = TypeVar("T")


def merged(first: T, second: T) -> T:
    if isinstance(first, Sequence) and isinstance(second, Sequence):
        return first + second
    if isinstance(first, Mapping) and isinstance(second, Mapping):
        return {
            key: merged(first.get(key, None), second.get(key, None))
            for key in first.keys() | second.keys()
        }
    if getattr(first, "merged_with", None) is not None:
        return first.merged_with(second)
    if getattr(second, "merged_with", None) is not None:
        return second.merged_with(first)
    return first or second


# Source Information


@dataclass_json
@dataclass
class Position:
    line: int
    column: Optional[int] = None

    def merged_with(self, other: Optional["Position"]) -> "Position":
        if other is not None:
            assert isinstance(other, Position)
            assert self.line == other.line
            return Position(
                line=self.line,
                column=merged(self.column, other.column),
            )
        return self


@dataclass_json
@dataclass
class Source:
    file_path: str
    text: Optional[str] = None
    start: Optional[Position] = None
    end: Optional[Position] = None

    def merged_with(self, other: Optional["Source"]) -> "Source":
        if other is not None:
            assert isinstance(other, Source)
            assert (
                self.file_path == other.file_path
            ), f"Mismatched file paths:\n{self}\n\n{other}"
            if self.text is not None and other.text is not None:
                assert self.text == other.text
            return Source(
                file_path=self.file_path,
                text=self.text or other.text,
                start=merged(self.start, other.start),
                end=merged(self.end, other.end),
            )
        return self

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
        package_info = dynamic.PythonDynamicPackageAnalysis.get_package_info()
        if package_info:
            file_path = str(Path(file_path).relative_to(package_info.package_root))
        start = Position(line=node.co_firstlineno)
        return Source(file_path, text=None, start=start)


# Context Matches

MatchesVar = TypeVar("MatchesVar", bound="TalonMatches")


@dataclass_json
@dataclass
class TalonMatches(ABC):
    @property
    def is_override(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def merged_with(self, other: Optional[MatchesVar]) -> MatchesVar:
        """
        Merge two Talon match contexts.
        """


@dataclass_json
@dataclass
class TalonModule(TalonMatches):
    @property
    def is_override(self) -> bool:
        return False

    def merged_with(self, other: Optional[MatchesVar]) -> MatchesVar:
        if other is not None:
            assert isinstance(other, TalonModule)
        return self


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

    def merged_with(self, other: Optional[MatchesVar]) -> MatchesVar:
        if other is not None:
            assert isinstance(other, TalonContext)
            return TalonContext(
                matches=merged(self.matches, other.matches),
                tags=merged(self.tags, other.tags),
            )
        else:
            return self


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

DeclType = TypeVar("DeclType", bound=ForwardRef("TalonDecl"))


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

    @abstractmethod
    def merged_with(self, other: Optional[DeclType]) -> DeclType:
        """
        Merge two Talon declarations.
        """


@dataclass_json
@dataclass
class TalonActionDecl(TalonDecl):
    source: Source = None
    impl: Optional[Callable] = field(
        default=None,
        metadata=config(encoder=_encode_function, decoder=_decode_function),
    )

    def __post_init__(self, **kwargs):
        if self.impl and not self.source:
            self.source = Source.from_code(self.impl.__code__)
        if self.impl and not self.desc:
            self.desc = self.impl.__doc__

    @property
    def sort(self):
        return TalonSort.Action

    def merged_with(self, other: Optional["TalonActionDecl"]) -> "TalonActionDecl":
        if other is not None:
            assert isinstance(other, TalonActionDecl)
            assert self.sort == other.sort
            assert self.name == other.name
            return TalonActionDecl(
                name=self.name,
                matches=merged(self.matches, other.matches),
                source=merged(self.source, other.source),
                desc=self.desc or other.desc,
                impl=self.impl or other.impl,
            )
        else:
            return self


@dataclass_json
@dataclass
class TalonCaptureDecl(TalonDecl):
    source: Source = None
    rule: Optional[TalonRule] = None
    impl: Optional[Callable] = field(
        default=None,
        metadata=config(encoder=_encode_type, decoder=_decode_type),
    )

    def __post_init__(self, **kwargs):
        if self.impl and not self.source:
            self.source = Source.from_code(self.impl.__code__)
        if self.impl and not self.desc:
            self.desc = self.impl.__doc__

    @property
    def sort(self):
        return TalonSort.Capture

    def merged_with(self, other: Optional["TalonCaptureDecl"]) -> "TalonCaptureDecl":
        if other is not None:
            assert isinstance(other, TalonCaptureDecl)
            assert self.sort == other.sort
            assert self.name == other.name
            return TalonCaptureDecl(
                name=self.name,
                matches=merged(self.matches, other.matches),
                source=merged(self.source, other.source),
                desc=self.desc or other.desc,
                rule=self.rule or other.rule,
                impl=self.impl or other.impl,
            )
        else:
            return self


ListValue = Union[dict[str, str], Sequence[str]]


@dataclass_json
@dataclass
class TalonListDecl(TalonDecl):
    list: Optional[ListValue] = None

    @property
    def sort(self):
        return TalonSort.List

    def __post_init__(self, **kwargs):
        if isinstance(self.list, Sequence):
            self.list = {word: word for word in self.list}

    def merged_with(self, other: Optional["TalonListDecl"]) -> "TalonListDecl":
        if other is not None:
            assert isinstance(other, TalonListDecl)
            assert self.sort == other.sort
            assert self.name == other.name
            return TalonListDecl(
                name=self.name,
                matches=merged(self.matches, other.matches),
                source=merged(self.source, other.source),
                desc=self.desc or other.desc,
                list=merged(self.list, other.list),
            )
        else:
            return self


@dataclass_json
@dataclass
class TalonTagDecl(TalonDecl):
    @property
    def sort(self):
        return TalonSort.Tag

    def merged_with(self, other: Optional["TalonTagDecl"]) -> "TalonTagDecl":
        if other is not None:
            assert isinstance(other, TalonTagDecl)
            assert self.sort == other.sort
            assert self.name == other.name
            return TalonTagDecl(
                name=self.name,
                matches=merged(self.matches, other.matches),
                source=merged(self.source, other.source),
                desc=self.desc or other.desc,
            )
        else:
            return self


@dataclass_json
@dataclass
class TalonModeDecl(TalonDecl):
    @property
    def sort(self):
        return TalonSort.Mode

    def merged_with(self, other: Optional["TalonModeDecl"]) -> "TalonModeDecl":
        if other is not None:
            assert isinstance(other, TalonModeDecl)
            assert self.sort == other.sort
            assert self.name == other.name
            return TalonModeDecl(
                name=self.name,
                matches=merged(self.matches, other.matches),
                source=merged(self.source, other.source),
                desc=self.desc or other.desc,
            )
        else:
            return self


SettingValue = any


@dataclass_json
@dataclass
class TalonSettingDecl(TalonDecl):
    type: Optional[Type] = field(
        default=None,
        metadata=config(encoder=_encode_type, decoder=_decode_type),
    )
    default: Optional[any] = None

    @property
    def sort(self):
        return TalonSort.Setting

    def merged_with(self, other: Optional["TalonSettingDecl"]) -> "TalonSettingDecl":
        if other is not None:
            assert isinstance(other, TalonSettingDecl)
            assert self.sort == other.sort
            assert self.name == other.name
            return TalonSettingDecl(
                name=self.name,
                matches=merged(self.matches, other.matches),
                source=merged(self.source, other.source),
                desc=self.desc or other.desc,
                type=self.type or other.type,
                default=self.default or other.default,
            )
        else:
            return self


@dataclass_json
@dataclass
class TalonDecls(Generic[DeclType]):
    sort: TalonSort
    declaration: DeclType = None
    overrides: list[DeclType] = field(default_factory=list)

    def merged_with(self, other: Optional["TalonDecls"]) -> "TalonDecls":
        if other is not None:
            assert isinstance(other, TalonDecls)
            assert self.sort == other.sort
            return TalonDecls(
                sort=self.sort,
                declaration=merged(self.declaration, other.declaration),
                overrides=merged(self.overrides, other.overrides),
            )
        else:
            return self


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
        if other is not None:
            assert isinstance(other, PythonFileInfo)
            assert (
                self.file_path == other.file_path
            ), f"Mismatched file paths:\n{self}\n\n{other}"
            assert (
                self.package_root == other.package_root
            ), f"Mismatched packages:\n{self}\n\n{other}"
            return PythonFileInfo(
                file_path=self.file_path,
                package_root=self.package_root,
                actions=merged(self.actions, other.actions),
                captures=merged(self.captures, other.captures),
                lists=merged(self.lists, other.lists),
                settings=merged(self.settings, other.settings),
                tags=merged(self.tags, other.tags),
                modes=merged(self.modes, other.modes),
                uses=merged(self.uses, other.uses),
            )
        else:
            return self


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
            except AttributeError as e:
                print(e)
                exit()
        return None

    def merged_with(self, other: Optional["PythonPackageInfo"]) -> "PythonPackageInfo":
        if other is not None:
            assert isinstance(other, PythonPackageInfo)
            assert self.package_root == other.package_root
            return PythonPackageInfo(
                package_root=self.package_root,
                file_infos=merged(self.file_infos, other.file_infos),
            )
        else:
            return self
