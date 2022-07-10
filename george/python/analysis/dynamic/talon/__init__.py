import inspect
from pathlib import Path
from george.types import *
import talon.ui as ui  # type: ignore
import talon.speech_system as speech_system  # type: ignore
import talon.cron as cron  # type: ignore
import talon.registry as registry  # type: ignore
import talon.settings as settings  # type: ignore
import talon.scope as scope  # type: ignore

from dataclasses import dataclass, field
from io import TextIOWrapper
from typing import *

import george.python.analysis.dynamic as dynamic
import sys


@dataclass
class Actions:
    def __init__(self):
        self.registered_actions = {}

    def action(self, action_path: str) -> Optional[Callable]:
        if action_path == "self":
            action_path = "user"
        try:
            dynamic.PythonDynamicPackageAnalysis.get_file_info().add_use(
                TalonSort.Action.name, action_path
            )
            return self.registered_actions[action_path]
        except KeyError:
            return dynamic.Stub()

    def _register_action(self, action_path: str, action_impl: Callable):
        if "." in action_path:
            scope, action_path = action_path.split(".", maxsplit=1)
            if not scope in self.registered_actions:
                self.registered_actions[scope] = Actions()
            self.registered_actions[scope]._register_action(action_path, action_impl)
        else:
            self.registered_actions[action_path] = action_impl

    def __getattr__(self, name: str) -> Optional[Callable]:
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return self.action(name)


class Module(dynamic.Stub):
    def __init__(self, desc: Optional[str] = None):
        self.desc = desc

    def action_class(self, cls: Type):
        global actions
        for name, func in inspect.getmembers(cls, inspect.isfunction):
            action_path = f"user.{name}"
            actions._register_action(action_path, func)
            file_path = Path(func.__code__.co_filename)
            file_path = file_path.relative_to(self._package_info.package_root)
            self._file_info.add_declaration(
                ActionDecl(
                    name=action_path,
                    file_path=str(file_path),
                    impl=func,
                )
            )

    def action(self, action_path: str) -> Optional[Callable]:
        global actions
        return actions.action(action_path)

    def capture(self, rule: str) -> Any:
        def __decorator(func: Callable):
            capture_path = f"user.{func.__code__.co_name}"
            file_path = Path(func.__code__.co_filename)
            file_path = file_path.relative_to(self._package_info.package_root)
            self._file_info.add_declaration(
                CaptureDecl(
                    name=capture_path,
                    file_path=str(file_path),
                    rule=TalonRule.parse(rule),
                    impl=func,
                )
            )
            return func

        return __decorator

    # def scope(self, func: "ScopeFunc") -> "ScopeDecl":
    #     return ScopeDecl(mod=self, func=func)

    # def setting(
    #     self,
    #     name: str,
    #     type: Type[Any],
    #     default: Union[Any, "SettingDecl.NoValueType"] = None,
    #     desc: str = None,
    # ) -> "SettingDecl":
    #     pass

    def list(self, name: str, desc: str = None):
        list_path = f"user.{name}"
        self._file_info.add_declaration(
            ListDecl(
                name=list_path,
                desc=desc,
            )
        )

    def mode(self, name: str, desc: str = None):
        mode_path = f"user.{name}"
        self._file_info.add_declaration(
            ModeDecl(
                name=mode_path,
                desc=desc,
            )
        )

    def tag(self, name: str, desc: str = None):
        tag_path = f"user.{name}"
        self._file_info.add_declaration(
            TagDecl(
                name=tag_path,
                matches=False,
                desc=desc,
            )
        )

    pass


class Context(dynamic.Stub):
    def __init__(self):
        self._matches = True
        self._decls = []
        pass

    def action_class(self, path: str):
        def __decorator(cls: Type):
            global actions
            for name, func in inspect.getmembers(cls, inspect.isfunction):
                action_path = f"user.{name}"
                file_path = Path(func.__code__.co_filename)
                file_path = file_path.relative_to(self._package_info.package_root)
                action_decl = ActionDecl(
                    name=action_path,
                    file_path=str(file_path),
                    matches=self.matches,
                    impl=func,
                )
                self._file_info.add_declaration(action_decl)
                self._decls.append(action_decl)

        return __decorator

    def action(self, action_path: str) -> Optional[Callable]:
        global actions
        return actions.action(action_path)

    def capture(self, path: str = None, rule: str = None) -> Any:
        def __decorator(func: Callable):
            capture_path = f"user.{func.__code__.co_name}"
            file_path = Path(func.__code__.co_filename)
            file_path = file_path.relative_to(self._package_info.package_root)
            capture_decl = CaptureDecl(
                name=capture_path,
                matches=self._matches,
                file_path=str(file_path),
                rule=TalonRule.parse(rule),
                impl=func,
            )
            self._file_info.add_declaration(capture_decl)
            self._decls.append(capture_decl)

        return __decorator

    @property
    def matches(self) -> Union[str, "Match"]:
        return self._matches

    @matches.setter
    def matches(self, matches: Union[str, "Match"]):
        self._matches = matches
        # talon.types.from_tree_sitter(talon.parse(f"{matches}\n-\n").root_node)
        for decl in self._decls:
            decl.matches = matches

    # @property
    # def apps(self):
    #     pass

    # @apps.setter
    # def apps(self, value: Sequence[str]):
    #     return []

    # @property
    # def lists(self) -> dict[str, Mapping[str, str]]:
    #     return {}

    # @lists.setter
    # def lists(self, lists: dict[str, Union[dict[str, str], Sequence[str]]]) -> None:
    #     pass

    # @property
    # def settings(self):
    #     return {}

    # @settings.setter
    # def settings(self, value: dict[str, "SettingValue"]):
    #     pass

    # @property
    # def tags(self):
    #     pass

    # @tags.setter
    # def tags(self, value: Sequence[str]):
    #     pass

    # @property
    # def commands(self) -> Mapping[str, CommandImpl]:
    #     pass

    # @property
    # def hotkeys(self) -> Mapping[str, ScriptImpl]:
    #     pass

    # @property
    # def noises(self):
    #     pass
    pass


class SettingDecl(dynamic.Stub):
    # class NoValueType:
    #     pass

    # NoValue: NoValueType = NoValueType()
    # mod: "Module"
    # path: str
    # type: Type
    # default: Union[Any, NoValueType]
    # desc: Optional[str]
    pass


class Settings(dynamic.Stub):
    # def lookup(self, path: str) -> SettingDecl:
    #     pass

    # def __contains__(self, path: str) -> bool:
    #     pass

    # def __getitem__(self, path: str) -> SettingValue:
    #     pass

    # def get(
    #     self,
    #     path: str,
    #     default: Union[SettingValue, SettingDecl.NoValueType, None] = None,
    # ) -> Optional[SettingValue]:
    #     pass

    # def list(self) -> None:
    #     pass
    pass


class ScopeDecl(dynamic.Stub):
    # mod: Module
    # func: ScopeFunc

    # def update(self, *args) -> None:
    #     pass
    pass


class Scope(dynamic.Stub):
    # app_decl: Any
    # lock: Any
    # registry: Any
    # data: Any
    # data_sources: Any
    # raw_data: Any
    # scopes: Any
    # registered: Any

    # def key(self, path: str) -> Tuple[str, Optional[str]]:
    #     pass

    # def get(self, path: str, default: Any = None) -> Any:
    #     pass

    # def __contains__(self, path: str) -> bool:
    #     pass

    # def __getitem__(self, path: str) -> Any:
    #     pass

    # def matches(self, cm: ContextMatch) -> bool:
    #     pass

    # def update(self, path: str) -> None:
    #     pass

    # def update_one(self, scope: ScopeDecl) -> None:
    #     pass

    # def update_decls(self, decls: Decls) -> None:
    #     pass
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


actions = Actions()
app = App()
resource = Resource()
