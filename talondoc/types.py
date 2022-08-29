import abc
import pathlib
import typing

from dataclasses import dataclass, field
from tree_sitter_talon import TalonCommandDeclaration, TalonExpression, TalonMatches


class ObjectEntry(abc.ABC):
    SORT: typing.ClassVar[str]

    @property
    def qualified_name(self) -> str:
        return f"{self.__class__.SORT}:{getattr(self, 'name')}"


@dataclass
class NamedObjectEntry(ObjectEntry):
    name: str


@dataclass
class FileEntry(ObjectEntry):
    path: pathlib.Path

    @property
    def name(self) -> str:
        return ".".join(self.path.parts)


@dataclass
class TalonFileEntry(FileEntry):
    SORT: typing.ClassVar[str] = "file"

    commands: list["CommandEntry"] = field(default_factory=list)
    matches: typing.Optional[TalonMatches] = None
    settings: list["SettingEntry"] = field(default_factory=list)
    tag_imports: list["TagEntry"] = field(default_factory=list)

    @property
    def name(self) -> str:
        return ".".join(self.path.parts)


@dataclass
class PackageEntry(FileEntry):
    SORT: typing.ClassVar[str] = "package"

    files: list[FileEntry] = field(default_factory=list)

    @property
    def name(self) -> str:
        return ".".join(self.path.parts)


@dataclass
class ActionEntry(NamedObjectEntry):
    SORT: typing.ClassVar[str] = "action"


@dataclass
class CaptureEntry(NamedObjectEntry):
    SORT: typing.ClassVar[str] = "capture"


@dataclass
class CommandEntry(ObjectEntry):
    SORT: typing.ClassVar[str] = "command"

    file: "TalonFileEntry"
    ast: TalonCommandDeclaration

    @property
    def name(self) -> str:
        # index = self.ast.start_position.line
        index = self.file.commands.index(self)
        return f"{self.file.name}.{index}"


@dataclass
class ContextEntry(NamedObjectEntry):
    SORT: typing.ClassVar[str] = "context"


@dataclass
class ListEntry(NamedObjectEntry):
    SORT: typing.ClassVar[str] = "list"


@dataclass
class ModeEntry(NamedObjectEntry):
    SORT: typing.ClassVar[str] = "mode"


@dataclass
class ModuleEntry(NamedObjectEntry):
    SORT: typing.ClassVar[str] = "module"


@dataclass
class SettingEntry(NamedObjectEntry):
    SORT: typing.ClassVar[str] = "setting"

    value: typing.Optional[TalonExpression] = None


@dataclass
class TagEntry(NamedObjectEntry):
    SORT: typing.ClassVar[str] = "tag"
