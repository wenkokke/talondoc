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
            encoder=lambda sort: sort.name, decoder=lambda name: TalonSort[name]
        )
    )
    file_path: str
    is_override: bool
    source: Source
    desc: Optional[str] = None


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
    declarations: dict[TalonSortName, dict[TalonDeclName, TalonDecl]] = field(
        default_factory=dict
    )
    overrides: dict[TalonSortName, dict[TalonDeclName, set[TalonDecl]]] = field(
        default_factory=dict
    )
    uses: dict[TalonSortName, set[TalonDeclName]] = field(default_factory=dict)

    def add(self, file_info: PythonFileInfo):
        self.file_infos[file_info.file_path] = file_info
        # Merge <file_info.declarations> into <self.declarations>
        for sort, declarations_for_sort in file_info.declarations.items():
            if not sort in self.declarations:
                self.declarations[sort] = {}
            for name, declaration in declarations_for_sort.items():
                self.declarations[sort][name] = declaration
        # Merge <file_info.overrides> into <self.overrides>
        for sort, overrides_for_sort in file_info.overrides.items():
            if not sort in self.overrides:
                self.overrides[sort] = {}
            for name, overrides_for_name in overrides_for_sort.items():
                if not name in self.overrides[sort]:
                    self.overrides[sort] = overrides_for_name
                else:
                    self.overrides[sort][name].update(overrides_for_name)
        # Merge <file_info.overrides> into <self.overrides>
        for sort, uses_for_sort in file_info.uses.items():
            if not sort in self.uses:
                self.uses[sort] = uses_for_sort
            else:
                self.uses[sort].update(uses_for_sort)


@dataclass_json
@dataclass(frozen=True)
class TalonRule:
    text: str


@dataclass_json
@dataclass(frozen=True)
class TalonScript:
    text: str


@dataclass_json
@dataclass(frozen=True)
class TalonCommand:
    rule: TalonRule
    script: TalonScript


@dataclass_json
@dataclass(frozen=True)
class TalonFileInfo:
    path: str
    commands: list[tuple[TalonRule, TalonScript]]
    uses: dict[TalonSortName, set[TalonDeclName]]
