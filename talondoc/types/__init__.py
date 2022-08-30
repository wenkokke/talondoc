import abc
import collections.abc
import pathlib
import typing

import dataclasses
import tree_sitter_talon


class ObjectEntry(abc.ABC):
    sort: typing.ClassVar[str]

    @property
    def qualified_name(self) -> str:
        return f"{self.__class__.sort}:{object.__getattribute__(self, 'name')}"


@dataclasses.dataclass
class NamedObjectEntry(ObjectEntry):
    name: str


@dataclasses.dataclass(init=False)
class PackageEntry(NamedObjectEntry):
    sort: typing.ClassVar[str] = "package"
    path: pathlib.Path
    files: list["FileEntry"] = dataclasses.field(default_factory=list)

    def __init__(
        self,
        path: pathlib.Path,
        files: list["FileEntry"] = [],
        *,
        name: typing.Optional[str] = None,
    ):
        self.path = path
        self.files = files
        self.name = name or self.path.parts[-1]


@dataclasses.dataclass
class FileEntry(ObjectEntry):
    sort: typing.ClassVar[str] = "file"
    package: PackageEntry
    path: pathlib.Path
    modules: list["ModuleEntry"] = dataclasses.field(default_factory=list)
    contexts: list["ContextEntry"] = dataclasses.field(default_factory=list)

    @property
    def name(self) -> str:
        return ".".join(self.path.parts)


@dataclasses.dataclass
class TalonFileEntry(FileEntry):
    commands: list["CommandEntry"] = dataclasses.field(default_factory=list)
    matches: typing.Optional[tree_sitter_talon.TalonMatches] = None
    settings: list["SettingEntry"] = dataclasses.field(default_factory=list)
    tag_imports: list["TagEntry"] = dataclasses.field(default_factory=list)

    @property
    def name(self) -> str:
        return ".".join(self.path.parts)


@dataclasses.dataclass
class PythonFileEntry(FileEntry):
    @property
    def name(self) -> str:
        return ".".join(self.path.parts)


@dataclasses.dataclass
class ContextEntry(ObjectEntry):
    sort: typing.ClassVar[str] = "context"
    file: PythonFileEntry
    desc: typing.Optional[str]

    @property
    def name(self) -> str:
        return ".".join((*self.file.path.parts, str(self.file.contexts.index(self))))

    @property
    def namespace(self) -> str:
        return self.file.package.name


@dataclasses.dataclass
class ModuleEntry(ObjectEntry):
    sort: typing.ClassVar[str] = "module"
    file: PythonFileEntry
    desc: typing.Optional[str]

    @property
    def name(self) -> str:
        return ".".join((*self.file.path.parts, str(self.file.modules.index(self))))

    @property
    def namespace(self) -> str:
        return self.file.package.name


@dataclasses.dataclass
class CallbackEntry(ObjectEntry):
    """
    Used to register callbacks into imported Python modules.
    """

    sort: typing.ClassVar[str] = "callback"
    callback: collections.abc.Callable[[], None]

    @property
    def name(self) -> str:
        return self.callback.__name__


@dataclasses.dataclass
class ActionEntry(NamedObjectEntry):
    sort: typing.ClassVar[str] = "action"
    module: typing.Union[ModuleEntry, ContextEntry]
    func: typing.Optional[collections.abc.Callable[..., typing.Any]] = None

    def __reduce__(self) -> tuple[collections.abc.Callable, tuple]:
        return (ActionEntry, (self.name, self.module, None))


@dataclasses.dataclass
class CaptureEntry(NamedObjectEntry):
    sort: typing.ClassVar[str] = "capture"


@dataclasses.dataclass
class CommandEntry(ObjectEntry):
    sort: typing.ClassVar[str] = "command"
    file: "TalonFileEntry"
    ast: tree_sitter_talon.TalonCommandDeclaration

    @property
    def name(self) -> str:
        # index = self.ast.start_position.line
        index = self.file.commands.index(self)
        return f"{self.file.name}.{index}"


@dataclasses.dataclass
class ListEntry(NamedObjectEntry):
    sort: typing.ClassVar[str] = "list"


@dataclasses.dataclass
class ModeEntry(NamedObjectEntry):
    sort: typing.ClassVar[str] = "mode"


@dataclasses.dataclass
class SettingEntry(NamedObjectEntry):
    sort: typing.ClassVar[str] = "setting"
    value: typing.Optional[tree_sitter_talon.TalonExpression] = None


@dataclasses.dataclass
class TagEntry(NamedObjectEntry):
    sort: typing.ClassVar[str] = "tag"
