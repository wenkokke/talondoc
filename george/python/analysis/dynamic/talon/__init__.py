from dataclasses import dataclass
from io import TextIOWrapper
from typing import *

import george.python.analysis.dynamic as dynamic
import sys

CommandImpl = Any
ScriptImpl = Any
ActionClassProxy = Any
ActionDecl = Any
Rule = Any
NameDecl = Any
ContextMatch = Any
Decls = Any


class AppNamespace(dynamic.Stub):
    pass


class Module:
    desc: Optional[str]
    apps: AppNamespace = AppNamespace()

    def action_class(self, cls: Any) -> ActionClassProxy:
        return cls

    def action(self, func: Any) -> ActionDecl:
        pass

    def capture(self, rule: Rule) -> Any:
        def __capture(func):
            return func

        return __capture

    def scope(self, func: "ScopeFunc") -> "ScopeDecl":
        return ScopeDecl(mod=self, func=func)

    def setting(
        self,
        name: str,
        type: Type[Any],
        default: Union[Any, "SettingDecl.NoValueType"] = None,
        desc: str = None,
    ) -> "SettingDecl":
        pass

    def list(self, name: str, desc: str = None) -> NameDecl:
        pass

    def mode(self, name: str, desc: str = None) -> NameDecl:
        pass

    def tag(self, name: str, desc: str = None) -> NameDecl:
        pass


class Context:
    name: str
    path: str
    desc: Optional[str]

    def action_class(self, path: str) -> Callable[[Any], ActionClassProxy]:
        def __decorator(cls):
            return cls

        return __decorator

    def action(self, path: str):
        def __action(*args):
            pass

        return __action

    def capture(self, path: str = None, *, rule: str = None) -> Any:
        def __decorator(func):
            return func

        return __decorator

    @property
    def matches(self) -> Union[str, "Match"]:
        return ""

    @matches.setter
    def matches(self, matches: Union[str, "Match"]):
        pass

    @property
    def apps(self):
        pass

    @apps.setter
    def apps(self, value: Sequence[str]):
        return []

    @property
    def lists(self) -> dict[str, Mapping[str, str]]:
        return {}

    @lists.setter
    def lists(self, lists: dict[str, Union[dict[str, str], Sequence[str]]]) -> None:
        pass

    @property
    def settings(self):
        return {}

    @settings.setter
    def settings(self, value: dict[str, "SettingValue"]):
        pass

    @property
    def tags(self):
        pass

    @tags.setter
    def tags(self, value: Sequence[str]):
        pass

    @property
    def commands(self) -> Mapping[str, CommandImpl]:
        pass

    @property
    def hotkeys(self) -> Mapping[str, ScriptImpl]:
        pass

    @property
    def noises(self):
        pass


SettingValue = Any


class SettingDecl:
    class NoValueType:
        pass

    NoValue: NoValueType = NoValueType()
    mod: "Module"
    path: str
    type: Type
    default: Union[Any, NoValueType]
    desc: Optional[str]


class Settings(dynamic.Register):
    def lookup(self, path: str) -> SettingDecl:
        pass

    def __contains__(self, path: str) -> bool:
        pass

    def __getitem__(self, path: str) -> SettingValue:
        pass

    def get(
        self,
        path: str,
        default: Union[SettingValue, SettingDecl.NoValueType, None] = None,
    ) -> Optional[SettingValue]:
        pass

    def list(self) -> None:
        pass


ScopeFunc = Callable[[], Dict]


@dataclass
class ScopeDecl:
    mod: Module
    func: ScopeFunc

    def update(self, *args) -> None:
        pass


class Scope:
    app_decl: Any
    lock: Any
    registry: Any
    data: Any
    data_sources: Any
    raw_data: Any
    scopes: Any
    registered: Any

    def key(self, path: str) -> Tuple[str, Optional[str]]:
        pass

    def get(self, path: str, default: Any = None) -> Any:
        pass

    def __contains__(self, path: str) -> bool:
        pass

    def __getitem__(self, path: str) -> Any:
        pass

    def matches(self, cm: ContextMatch) -> bool:
        pass

    def update(self, path: str) -> None:
        pass

    def update_one(self, scope: ScopeDecl) -> None:
        pass

    def update_decls(self, decls: Decls) -> None:
        pass


class Resource(dynamic.Stub):
    def open(self, file: str, mode: str) -> TextIOWrapper:
        return open(file, mode)


class App(dynamic.Stub):
    platform: str = {
        "linux": "linux",
        "darwin": "mac",
        "win32": "windows",
    }[sys.platform]


actions = dynamic.Stub()
scope = dynamic.Stub()
settings = dynamic.Stub()
registry = dynamic.Stub()
ui = dynamic.Stub()
app = App()
resource = Resource()
speech_system = dynamic.Stub()
cron = dynamic.Stub()