from dataclasses import dataclass, field
from dataclasses_json import config, dataclass_json
from enum import Enum
from typing import Generator, Optional
import ast

from george.analysis.talon.info import (
    TalonDecl,
    TalonDeclName,
    TalonSort,
    TalonSortName,
)


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
        for file_path, file_info in self.file_infos.items():
            if sort in file_info.declarations and name in file_info.declarations[sort]:
                return file_info.declarations[sort][name]

    def overrides(
        self, sort: TalonSortName, name: TalonDeclName
    ) -> Generator[TalonDecl, None, None]:
        for file_path, file_info in self.file_infos.items():
            if sort in file_info.overrides and name in file_info.overrides[sort]:
                for override in file_info.overrides[sort][name]:
                    yield override

    def uses(
        self, sort: TalonSortName, name: TalonDeclName
    ) -> Generator[str, None, None]:
        for file_path, file_info in self.file_infos.items():
            if sort in file_info.overrides and name in file_info.uses[sort]:
                yield file_path
