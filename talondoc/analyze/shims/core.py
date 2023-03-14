import inspect
import platform
import types
from collections.abc import Callable, Iterator
from io import TextIOWrapper
from types import ModuleType
from typing import Any, Mapping, Optional, Sequence, cast

from ..entries.user import (
    EventCode,
    ListValue,
    SettingValue,
    UserActionEntry,
    UserCallbackEntry,
    UserCaptureEntry,
    UserContextEntry,
    UserFunctionEntry,
    UserListEntry,
    UserModeEntry,
    UserModuleEntry,
    UserPythonFileEntry,
    UserSettingEntry,
    UserTagEntry,
)
from ..registry import Registry


class ObjectShim:
    """
    A simple shim which responds to any method.
    """

    def register(self, event_code: EventCode, func: Callable[..., Any]):
        file = Registry.get_active_file()
        assert isinstance(file, UserPythonFileEntry)
        callback_entry = UserCallbackEntry(
            parent=file,
            func=func,
            event_code=event_code,
        )
        Registry.get_active_global_registry().register(callback_entry)

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name: str) -> Any:
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return self

    def __setattr__(self, name: str, value: Any):
        object.__setattr__(self, name, value)

    def __getitem__(self, name: str) -> Any:
        return self

    def __setitem__(self, name: str, value: Any):
        pass

    def __enter__(self) -> Any:
        return self

    def __exit__(self, *args):
        pass

    def __add__(self, other) -> Any:
        return self

    def __sub__(self, other) -> Any:
        return self

    def __mul__(self, other) -> Any:
        return self

    def __pow__(self, other) -> Any:
        return self

    def __mod__(self, other) -> Any:
        return self

    def __floordiv__(self, other) -> Any:
        return self

    def __truediv__(self, other) -> Any:
        return self

    def __radd__(self, other) -> Any:
        return self

    def __rsub__(self, other) -> Any:
        return self

    def __rmul__(self, other) -> Any:
        return self

    def __rmod__(self, other) -> Any:
        return self

    def __rfloordiv__(self, other) -> Any:
        return self

    def __rtruediv__(self, other) -> Any:
        return self

    def __abs__(self) -> Any:
        return self

    def __neg__(self) -> Any:
        return self

    def __trunc__(self) -> Any:
        return self

    def __floor__(self) -> Any:
        return self

    def __ceil__(self) -> Any:
        return self

    def __and__(self, other) -> Any:
        return self

    def __rand__(self, other) -> Any:
        return self

    def __or__(self, other) -> Any:
        return self

    def __ror__(self, other) -> Any:
        return self

    def __xor__(self, other) -> Any:
        return self

    def __rxor__(self, other) -> Any:
        return self

    def __invert__(self) -> Any:
        return self

    def __lshift__(self, other) -> Any:
        return self

    def __rlshift__(self, other) -> Any:
        return self

    def __rshift__(self, other) -> Any:
        return self

    def __rrshift__(self, other) -> Any:
        return self

    def __call__(self, *args, **kwargs) -> Any:
        return self

    def __iter__(self) -> Iterator:
        return ().__iter__()


class ModuleShim(ModuleType):
    """
    A module shim which defines any value.
    """

    def __init__(self, fullname: str):
        super().__init__(fullname)

    def __getattr__(self, name: str) -> Any:
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return ObjectShim()


def _action(
    registry: Registry, name: str, *, namespace: Optional[str] = None
) -> Optional[Callable[..., Any]]:
    action_group_entry = registry.lookup(UserActionEntry, name, namespace=namespace)
    if action_group_entry and action_group_entry.default:
        function_name = action_group_entry.default.func
        if function_name:
            function_entry = registry.lookup(UserFunctionEntry, function_name)
            if function_entry:
                return function_entry.func
    return ObjectShim()  # type: ignore


class TalonActionsShim:
    def __getattr__(self, name: str) -> Optional[Callable[..., Any]]:
        try:
            return cast(
                Optional[Callable[..., Any]],
                object.__getattribute__(self, name),
            )
        except AttributeError:
            registry = Registry.get_active_global_registry()
            package = registry.active_package_entry
            namespace = package.get_namespace() if package else None
            return _action(registry, name, namespace=namespace)


class TalonAppShim(ObjectShim):
    @property
    def platform(self) -> str:
        system = platform.system()
        if system == "Linux":
            return "linux"
        if system == "Darwin":
            return "mac"
        if system == "Windows":
            return "windows"
        raise ValueError(system)


class TalonContextListsShim(Mapping[str, ListValue]):
    def __init__(self, context: "TalonShim.Context"):
        self._context = context

    def _add_list_value(self, name: str, value: ListValue):
        namespace = self._context._module_entry.get_namespace()
        list_entry = UserListEntry(
            name=f"{namespace}.{name}",
            parent=self._context._module_entry,
            value=value,
        )
        Registry.get_active_global_registry().register(list_entry)

    def __setitem__(self, name: str, value: ListValue):
        self._add_list_value(name, value)

    def update(self, values: Mapping[str, ListValue]):
        for name, value in values.items():
            self._add_list_value(name, value)

    def __getitem__(self):
        raise NotImplementedError

    def __iter__(self):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError


class TalonContextSettingsShim(Mapping):
    def __init__(self, context: "TalonShim.Context"):
        self._context = context

    def _add_setting_value(self, name: str, value: SettingValue):
        namespace = self._context._module_entry.get_namespace()
        setting_entry = UserSettingEntry(
            name=f"{namespace}.{name}",
            parent=self._context._module_entry,
            value=value,
        )
        Registry.get_active_global_registry().register(setting_entry)

    def __setitem__(self, name: str, value: SettingValue):
        self._add_setting_value(name, value)

    def update(self, values: Mapping[str, SettingValue]):
        for name, value in values.items():
            self._add_setting_value(name, value)

    def __getitem__(self):
        raise NotImplementedError

    def __iter__(self):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError


class TalonContextTagsShim(Sequence):
    def __init__(self, context: "TalonShim.Context"):
        self._context = context

    def _add_tag_import(self, name: str):
        # TODO: add use entries
        pass

    def __setitem__(self, name: str):
        self._add_tag_import(name)

    def update(self, values: Sequence[str]):
        for name in values:
            self._add_tag_import(name)

    def __getitem__(self):
        raise NotImplementedError

    def __iter__(self):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError


class TalonResourceShim(ObjectShim):
    def open(self, file: str, mode: str) -> TextIOWrapper:
        return cast(TextIOWrapper, open(file, mode))

    def read(self, file: str) -> str:
        raise NotImplementedError

    def write(self, file: str, contents: str) -> str:
        raise NotImplementedError


class TalonShim(ModuleShim):
    """
    A shim for the 'talon' module.
    """

    def __init__(self):
        super().__init__("talon")
        self.actions = TalonActionsShim()
        self.app = TalonAppShim()
        self.resource = TalonResourceShim()
        # TODO: app
        # TODO: ui

    class Module(ObjectShim):
        def __init__(self, desc: Optional[str] = None):
            file = Registry.get_active_file()
            assert isinstance(file, UserPythonFileEntry)
            self._module_entry = UserModuleEntry(parent=file, desc=desc)
            Registry.get_active_global_registry().register(self._module_entry)

        def action_class(self, cls: type):
            for name, func in inspect.getmembers(cls, inspect.isfunction):
                assert inspect.isfunction(func)
                registry = Registry.get_active_global_registry()
                function_entry = UserFunctionEntry(
                    func=func,
                    parent=self._module_entry.parent,
                )
                function_entry.set_location(func.__code__.co_firstlineno)
                registry.register(function_entry)
                action_entry = UserActionEntry(
                    parent=self._module_entry,
                    name=f"{self._module_entry.get_namespace()}.{name}",
                    desc=func.__doc__,
                    func=function_entry.get_name(),
                )
                action_entry.set_location(func.__code__.co_firstlineno)
                registry.register(action_entry)

        def action(self, name: str) -> Optional[Callable[..., Any]]:
            registry = Registry.get_active_global_registry()
            namespace = self._module_entry.get_namespace()
            return _action(registry, name, namespace=namespace)  # type: ignore

        def capture(
            self, rule: str
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def __decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                namespace = self._module_entry.get_namespace()
                registry = Registry.get_active_global_registry()
                function_entry = UserFunctionEntry(
                    func=func,
                    parent=self._module_entry.parent,
                )
                function_entry.set_location(func.__code__.co_firstlineno)
                registry.register(function_entry)
                capture_entry = UserCaptureEntry(
                    name=f"{namespace}.{func.__name__}",
                    parent=self._module_entry,
                    rule=rule,
                    desc=func.__doc__,
                    func=function_entry.get_name(),
                )
                capture_entry.set_location(func.__code__.co_firstlineno)
                registry.register(capture_entry)
                return func

            return __decorator

        def setting(
            self,
            name: str,
            type: type,
            default: SettingValue = None,
            desc: str = None,
        ):
            namespace = self._module_entry.get_namespace()
            setting_entry = UserSettingEntry(
                name=f"{namespace}.{name}",
                parent=self._module_entry,
                type=type.__name__,
                desc=desc,
                value=default,
            )
            Registry.get_active_global_registry().register(setting_entry)

        def list(self, name: str, desc: str = None):
            namespace = self._module_entry.get_namespace()
            list_entry = UserListEntry(
                name=f"{namespace}.{name}",
                parent=self._module_entry,
                desc=desc,
            )
            Registry.get_active_global_registry().register(list_entry)

        def mode(self, name: str, desc: str = None):
            namespace = self._module_entry.get_namespace()
            mode_entry = UserModeEntry(
                name=f"{namespace}.{name}",
                parent=self._module_entry,
                desc=desc,
            )
            Registry.get_active_global_registry().register(mode_entry)

        def tag(self, name: str, desc: str = None):
            namespace = self._module_entry.get_namespace()
            tag_entry = UserTagEntry(
                name=f"{namespace}.{name}",
                parent=self._module_entry,
                desc=desc,
            )
            Registry.get_active_global_registry().register(tag_entry)

        # TODO: apps
        # TODO: scope

    class Context(ObjectShim):
        def __init__(self, desc: Optional[str] = None):
            file = Registry.get_active_file()
            assert isinstance(file, UserPythonFileEntry)
            self._module_entry = UserContextEntry(parent=file, desc=desc)
            Registry.get_active_global_registry().register(self._module_entry)
            self._lists = TalonContextListsShim(self)
            self._settings = TalonContextSettingsShim(self)
            self._tags = TalonContextTagsShim(self)
            # TODO: matches
            # TODO: apps

        @property
        def lists(self) -> Mapping[str, ListValue]:
            return self._lists

        @lists.setter
        def lists(self, lists: Mapping[str, ListValue]) -> None:
            self._lists.update(lists)

        @property
        def settings(self) -> Mapping[str, SettingValue]:
            return self._settings

        @settings.setter
        def settings(self, values: Mapping[str, SettingValue]):
            self._settings.update(values)

        @property
        def tags(self) -> Sequence[str]:
            return self._tags

        @tags.setter
        def tags(self, values: Sequence[str]):
            self._tags.update(values)

        def action_class(self, namespace: str) -> Callable[[type], type]:
            def __decorator(cls: type):
                for name, func in inspect.getmembers(cls, inspect.isfunction):
                    registry = Registry.get_active_global_registry()
                    function_entry = UserFunctionEntry(
                        func=func,
                        parent=self._module_entry.parent,
                    )
                    function_entry.set_location(func.__code__.co_firstlineno)
                    registry.register(function_entry)
                    name = f"{namespace}.{name}"
                    action_entry = UserActionEntry(
                        parent=self._module_entry,
                        name=name,
                        desc=func.__doc__,
                        func=function_entry.get_name(),
                    )
                    action_entry.set_location(func.__code__.co_firstlineno)
                    registry.register(action_entry)

            return __decorator

        def action(self, name: str) -> Optional[Callable[..., Any]]:
            registry = Registry.get_active_global_registry()
            namespace = self._module_entry.get_namespace()
            return _action(registry, name, namespace=namespace)

        def capture(
            self, namespace: Optional[str] = None, rule: Optional[str] = None
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            namespace = namespace or self._module_entry.get_namespace()

            def __decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                if rule is None:
                    raise ValueError("Missing rule")

                function_entry = UserFunctionEntry(
                    func=func,
                    parent=self._module_entry.parent,
                )
                function_entry.set_location(func.__code__.co_firstlineno)
                capture_entry = UserCaptureEntry(
                    name=f"{namespace}.{func.__name__}",
                    parent=self._module_entry,
                    rule=rule,
                    desc=func.__doc__,
                    func=function_entry.get_name(),
                )
                capture_entry.set_location(func.__code__.co_firstlineno)
                registry = Registry.get_active_global_registry()
                registry.register(function_entry)
                registry.register(capture_entry)
                return func

            return __decorator
