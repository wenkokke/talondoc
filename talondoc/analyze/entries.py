import abc
import dataclasses
import pathlib
from collections.abc import Callable
from typing import Any, ClassVar, Generic, Optional, TypeVar, Union, cast

import tree_sitter_talon


@dataclasses.dataclass(frozen=True)
class DuplicateEntry(Exception):
    """
    Raised when an entry is defined in multiple modules.
    """

    entry1: "ModuleObjectEntry"
    entry2: "ModuleObjectEntry"

    def __str__(self) -> str:
        return "\n".join(
            [
                f"Action '{self.entry1.name}' is declared by multiple modules:",
                f"-  {self.entry1.module.file.path}",
                f"-  {self.entry2.module.file.path}",
            ]
        )


def resolve_name(name: str, *, namespace: Optional[str] = None) -> str:
    parts = name.split(".")
    if parts and parts[0] == "self":
        if namespace:
            return ".".join([namespace, *parts[1:]])
        else:
            raise ValueError(f"Cannot resolve 'self' in {name}")
    else:
        return name


ListValue = Union[list[str], dict[str, Any]]

SettingValue = Any


class ObjectEntry(abc.ABC):
    sort: ClassVar[str]

    @property
    def namespace(self) -> str:
        if isinstance(self, PackageEntry):
            return cast(str, object.__getattribute__(self, "name"))
        elif hasattr(self, "package"):
            package = object.__getattribute__(self, "package")
            assert isinstance(package, PackageEntry)
            return package.name
        elif hasattr(self, "file"):
            file = object.__getattribute__(self, "file")
            assert isinstance(file, FileEntry)
            return file.package.name
        elif hasattr(self, "module"):
            module = object.__getattribute__(self, "module")
            assert isinstance(module, ModuleEntry)
            return module.file.package.name
        elif hasattr(self, "file_or_module"):
            file_or_module = object.__getattribute__(self, "file_or_module")
            assert isinstance(file_or_module, (FileEntry, ModuleEntry))
            return file_or_module.namespace
        else:
            raise TypeError(type(self))

    @property
    def resolved_name(self) -> str:
        name = object.__getattribute__(self, "name")
        return resolve_name(name, namespace=self.namespace)

    @property
    def qualified_name(self) -> str:
        return f"{self.__class__.sort}:{self.resolved_name}"


@dataclasses.dataclass
class FunctionEntry(ObjectEntry):
    sort: ClassVar[str] = "function"
    func: Callable[..., Any]

    @property
    def name(self) -> str:
        return self.func.__qualname__

    @property
    def resolved_name(self) -> str:
        return self.name


@dataclasses.dataclass(init=False)
class PackageEntry(ObjectEntry):
    sort: ClassVar[str] = "package"
    name: str
    path: pathlib.Path
    files: list["FileEntry"] = dataclasses.field(default_factory=list)

    def __init__(
        self,
        path: pathlib.Path,
        files: list["FileEntry"] = [],
        *,
        name: Optional[str] = None,
    ):
        self.path = path
        self.files = files
        self.name = name or self.path.parts[-1]


@dataclasses.dataclass()
class FileEntry(ObjectEntry):
    sort: ClassVar[str] = "file"
    package: PackageEntry = dataclasses.field(repr=False)
    path: pathlib.Path

    def __post_init__(self, *args, **kwargs):
        assert self not in self.package.files
        self.package.files.append(self)

    @property
    def name(self) -> str:
        return ".".join((self.namespace, *self.path.parts))


@dataclasses.dataclass()
class TalonFileEntry(FileEntry):
    commands: list["CommandEntry"] = dataclasses.field(default_factory=list)
    matches: Optional[tree_sitter_talon.TalonMatches] = None
    settings: list["SettingValueEntry"] = dataclasses.field(default_factory=list)
    tag_imports: list["TagImportEntry"] = dataclasses.field(default_factory=list)


@dataclasses.dataclass()
class PythonFileEntry(FileEntry):
    modules: list["ModuleEntry"] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class ModuleEntry(ObjectEntry):
    sort: ClassVar[str] = "module"
    file: PythonFileEntry = dataclasses.field(repr=False)
    desc: Optional[str]

    def __post_init__(self, *args, **kwargs):
        self._index = len(self.file.modules)
        self.file.modules.append(self)

    @property
    def name(self) -> str:
        return ".".join(
            [
                self.namespace,
                *self.file.path.parts,
                str(self._index),
            ]
        )


@dataclasses.dataclass
class ContextEntry(ModuleEntry):
    sort: ClassVar[str] = "context"
    matches: Union[None, str, tree_sitter_talon.TalonMatches] = None


EventCode = Union[int, str]


@dataclasses.dataclass
class CallbackEntry(ObjectEntry):
    """
    Used to register callbacks into imported Python modules.
    """

    sort: ClassVar[str] = "callback"
    event_code: EventCode
    callback: Callable[..., None]
    file: FileEntry = dataclasses.field(repr=False)

    @property
    def name(self) -> str:
        return str(self.event_code)


@dataclasses.dataclass
class ModuleObjectEntry(ObjectEntry):
    name: str
    module: ModuleEntry = dataclasses.field(repr=False)


ModuleObjectEntryVar = TypeVar("ModuleObjectEntryVar", bound=ModuleObjectEntry)


@dataclasses.dataclass
class ModuleObjectGroupEntry(ObjectEntry, Generic[ModuleObjectEntryVar]):
    name: str
    default: Optional[ModuleObjectEntryVar] = None
    overrides: list[ModuleObjectEntryVar] = dataclasses.field(default_factory=list)

    def append(self, entry: "ModuleObjectEntryVar"):
        assert self.resolved_name == entry.resolved_name, "\n".join(
            [
                f"Cannot append entry with different name to a group:",
                f"- group name: {self.resolved_name}",
                f"- entry name: {entry.resolved_name}",
            ]
        )
        if isinstance(entry.module, ContextEntry):
            self.overrides.append(entry)
        else:
            assert isinstance(
                entry.module, ModuleEntry
            ), f"Entry does not belong to any module: {entry.module}"
            if self.default is not None:
                raise DuplicateEntry(self.default, entry)
            self.default = entry

    @property
    def namespace(self) -> str:
        if self.default:
            return self.default.namespace
        else:
            for override in self.overrides:
                return override.namespace
        raise ValueError(self)


@dataclasses.dataclass
class ActionEntry(ModuleObjectEntry):
    sort: ClassVar[str] = "action"
    desc: Optional[str]
    func: Optional[str]

    def __post_init__(self, *args, **kwargs):
        # TODO: add self to module
        pass

    def group(self) -> "ActionGroupEntry":
        if isinstance(self.module, ContextEntry):
            return ActionGroupEntry(name=self.name, overrides=[self])
        else:
            assert isinstance(self.module, ModuleEntry)
            return ActionGroupEntry(name=self.name, default=self)


@dataclasses.dataclass
class ActionGroupEntry(ModuleObjectGroupEntry[ActionEntry]):
    sort: ClassVar[str] = "action-group"


@dataclasses.dataclass
class CaptureEntry(ObjectEntry):
    sort: ClassVar[str] = "capture"
    name: str
    module: ModuleEntry = dataclasses.field(repr=False)
    rule: Union[str, tree_sitter_talon.TalonRule]
    desc: Optional[str]
    func: Optional[str]

    def __post_init__(self, *args, **kwargs):
        # TODO: add self to module
        pass


@dataclasses.dataclass
class CommandEntry(ObjectEntry):
    sort: ClassVar[str] = "command"
    file: TalonFileEntry = dataclasses.field(repr=False)
    ast: tree_sitter_talon.TalonCommandDeclaration

    def __post_init__(self, *args, **kwargs):
        self._index = len(self.file.commands)
        assert self not in self.file.commands
        self.file.commands.append(self)

    @property
    def name(self) -> str:
        return f"{self.file.name}.{self._index}"


@dataclasses.dataclass
class ListEntry(ObjectEntry):
    sort: ClassVar[str] = "list"
    name: str
    module: ModuleEntry = dataclasses.field(repr=False)
    desc: Optional[str] = None
    value: Optional[ListValue] = None

    def __post_init__(self, *args, **kwargs):
        # TODO: add self to module
        pass


@dataclasses.dataclass
class ListValueEntry(ObjectEntry):
    sort: ClassVar[str] = "list-value"
    name: str
    module: ModuleEntry = dataclasses.field(repr=False)
    value: ListValue

    def __post_init__(self, *args, **kwargs):
        # TODO: add self to module
        pass


@dataclasses.dataclass
class ModeEntry(ObjectEntry):
    sort: ClassVar[str] = "mode"
    name: str
    module: ModuleEntry = dataclasses.field(repr=False)
    desc: Optional[str] = None

    def __post_init__(self, *args, **kwargs):
        # TODO: add self to module
        pass


@dataclasses.dataclass
class SettingEntry(ObjectEntry):
    sort: ClassVar[str] = "setting"
    name: str
    module: ModuleEntry = dataclasses.field(repr=False)
    type: Optional[type] = None
    desc: Optional[str] = None
    default: Optional[tree_sitter_talon.TalonExpression] = None

    def __post_init__(self, *args, **kwargs):
        # TODO: add self to module
        pass


@dataclasses.dataclass
class SettingValueEntry(ObjectEntry):
    sort: ClassVar[str] = "setting-value"
    name: str
    file_or_module: Union[TalonFileEntry, ModuleEntry] = dataclasses.field(repr=False)
    value: tree_sitter_talon.TalonExpression

    def __post_init__(self, *args, **kwargs):
        if isinstance(self.file_or_module, TalonFileEntry):
            assert self not in self.file_or_module.settings
            self.file_or_module.settings.append(self)


@dataclasses.dataclass
class TagEntry(ObjectEntry):
    sort: ClassVar[str] = "tag"
    name: str
    module: ModuleEntry = dataclasses.field(repr=False)
    desc: Optional[str] = None

    def __post_init__(self, *args, **kwargs):
        # TODO: add self to module
        pass


@dataclasses.dataclass
class TagImportEntry(ObjectEntry):
    sort: ClassVar[str] = "tag-import"
    name: str
    file_or_module: Union[TalonFileEntry, ModuleEntry] = dataclasses.field(repr=False)

    def __post_init__(self, *args, **kwargs):
        if isinstance(self.file_or_module, TalonFileEntry):
            assert self not in self.file_or_module.tag_imports
            self.file_or_module.tag_imports.append(self)
