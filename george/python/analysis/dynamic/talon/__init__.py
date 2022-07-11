import inspect
from pathlib import Path
import talon.ui as ui  # type: ignore
import talon.speech_system as speech_system  # type: ignore
import talon.cron as cron  # type: ignore
import talon.registry as registry  # type: ignore
import talon.settings as settings  # type: ignore
import talon.scope as scope  # type: ignore

from dataclasses import dataclass, field
from io import TextIOWrapper
from typing import *

from george.types import *
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


class Module:
    def __init__(self, desc: Optional[str] = None):
        self.desc = desc

    @property
    def _package_info(self) -> PythonPackageInfo:
        return dynamic.PythonDynamicPackageAnalysis.get_package_info()

    @property
    def _file_info(self) -> PythonFileInfo:
        return dynamic.PythonDynamicPackageAnalysis.get_file_info()

    def action_class(self, cls: Type):
        global actions
        for name, func in inspect.getmembers(cls, inspect.isfunction):
            action_path = f"user.{name}"
            actions._register_action(action_path, func)
            file_path = Path(func.__code__.co_filename)
            file_path = file_path.relative_to(self._package_info.package_root)
            self._file_info.add_declaration(
                TalonActionDecl(
                    name=action_path,
                    matches=TalonModule(),
                    impl=func,
                )
            )

    def action(self, action_path: str) -> Optional[Callable]:
        global actions
        return actions.action(action_path)

    @property
    def apps(self):
        return dynamic.Stub()

    @apps.setter
    def apps(self, value: Sequence[str]):
        # TODO: save apps information
        pass

    def capture(self, rule: str) -> Any:
        def __decorator(func: Callable):
            capture_path = f"user.{func.__code__.co_name}"
            file_path = Path(func.__code__.co_filename)
            file_path = file_path.relative_to(self._package_info.package_root)
            self._file_info.add_declaration(
                TalonCaptureDecl(
                    name=capture_path,
                    matches=TalonModule(),
                    rule=TalonRule.parse(rule),
                    impl=func,
                )
            )
            return func

        return __decorator

    def scope(self, func: Callable) -> any:
        # TODO: save scope information
        return dynamic.Stub()

    def setting(
        self,
        name: str,
        type: Type,
        default: any = None,
        desc: str = None,
    ):
        setting_path = f"user.{name}"
        self._file_info.add_declaration(
            TalonSettingDecl(
                name=setting_path,
                matches=TalonModule(),
                source=Source(file_path=self._file_info.file_path),
                desc=desc,
                type=type,
                default=default,
            )
        )

    def list(self, name: str, desc: str = None):
        list_path = f"user.{name}"
        self._file_info.add_declaration(
            TalonListDecl(
                name=list_path,
                matches=TalonModule(),
                source=Source(file_path=self._file_info.file_path),
                desc=desc,
            )
        )

    def mode(self, name: str, desc: str = None):
        mode_path = f"user.{name}"
        self._file_info.add_declaration(
            TalonModeDecl(
                name=mode_path,
                matches=TalonModule(),
                source=Source(file_path=self._file_info.file_path),
                desc=desc,
            )
        )

    def tag(self, name: str, desc: str = None):
        tag_path = f"user.{name}"
        self._file_info.add_declaration(
            TalonTagDecl(
                name=tag_path,
                matches=TalonModule(),
                source=Source(file_path=self._file_info.file_path),
                desc=desc,
            )
        )


class Context:
    class Lists(Mapping):
        def __init__(self, context: "Context"):
            self.context = context

        def _add_list_declaration(self, name: str, value: ListValue):
            self.context._file_info.add_declaration(
                TalonListDecl(
                    name=name,
                    matches=self.context._matches,
                    source=Source(file_path=self.context._file_info.file_path),
                    list=value,
                )
            )

        def __setitem__(self, name: str, value: ListValue):
            self._add_list_declaration(name, value)

        def update(self, values: dict[str, ListValue]):
            for name, value in values.items():
                self._add_list_declaration(name, value)

        def __getitem__(self):
            raise NotImplementedError

        def __iter__(self):
            raise NotImplementedError

        def __len__(self):
            raise NotImplementedError

    class Settings(Mapping):
        def __init__(self, context: "Context"):
            self.context = context

        def _add_setting_declaration(self, name: str, value: SettingValue):
            self.context._file_info.add_declaration(
                TalonSettingDecl(
                    name=name,
                    matches=self.context._matches,
                    source=Source(file_path=self.context._file_info.file_path),
                    type=type(value),
                    default=value,
                )
            )

        def __setitem__(self, name: str, value: SettingValue):
            self._add_setting_declaration(name, value)

        def update(self, values: dict[str, SettingValue]):
            for name, value in values.items():
                self._add_setting_declaration(name, value)

        def __getitem__(self):
            raise NotImplementedError

        def __iter__(self):
            raise NotImplementedError

        def __len__(self):
            raise NotImplementedError

    def __init__(self):
        self._matches = TalonContext()
        self._lists = Context.Lists(self)
        self._settings = Context.Settings(self)

    @property
    def _package_info(self) -> PythonPackageInfo:
        return dynamic.PythonDynamicPackageAnalysis.get_package_info()

    @property
    def _file_info(self) -> PythonFileInfo:
        return dynamic.PythonDynamicPackageAnalysis.get_file_info()

    def action_class(self, path: str):
        def __decorator(cls: Type):
            global actions
            for name, func in inspect.getmembers(cls, inspect.isfunction):
                action_path = f"{path}.{name}"
                file_path = Path(func.__code__.co_filename)
                file_path = file_path.relative_to(self._package_info.package_root)
                self._file_info.add_declaration(
                    TalonActionDecl(
                        name=action_path,
                        matches=self._matches,
                        impl=func,
                    )
                )

        return __decorator

    def action(self, action_path: str) -> Optional[Callable]:
        global actions
        return actions.action(action_path)

    def capture(self, path: str = None, rule: str = None) -> Any:
        def __decorator(func: Callable):
            capture_path = f"{path}.{func.__code__.co_name}"
            file_path = Path(func.__code__.co_filename)
            file_path = file_path.relative_to(self._package_info.package_root)
            self._file_info.add_declaration(
                TalonCaptureDecl(
                    name=capture_path,
                    matches=self._matches,
                    rule=TalonRule.parse(rule),
                    impl=func,
                )
            )

        return __decorator

    @property
    def matches(self) -> TalonMatches:
        return self._matches

    @matches.setter
    def matches(self, matches: str):
        self._matches.matches = TalonContext.parse(matches)

    @property
    def apps(self):
        raise NotImplementedError

    @apps.setter
    def apps(self, value: Sequence[str]):
        raise NotImplementedError

    @property
    def lists(self) -> dict[str, ListValue]:
        return self._lists

    @lists.setter
    def lists(self, lists: dict[str, ListValue]) -> None:
        self._lists.update(lists)

    @property
    def settings(self) -> dict[str, any]:
        return self._settings

    @settings.setter
    def settings(self, values: dict[str, any]):
        self._settings.update(values)

    @property
    def tags(self):
        raise NotImplementedError

    @tags.setter
    def tags(self, tag_names: Sequence[str]):
        for tag_name in tag_names:
            self._matches.tags.append(tag_name)


class Settings(dynamic.Stub):
    pass


class Scope(dynamic.Stub):
    pass


class Resource(dynamic.Stub):
    def open(self, file: str, mode: str) -> TextIOWrapper:
        return open(file, mode)

    def read(self, file: str) -> str:
        raise NotImplementedError

    def write(self, file: str, contents: str) -> str:
        raise NotImplementedError


class App(dynamic.Stub):
    platform: str = {
        "linux": "linux",
        "darwin": "mac",
        "win32": "windows",
    }[sys.platform]


actions = Actions()
app = App()
resource = Resource()
