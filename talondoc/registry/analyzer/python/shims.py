import inspect
import platform
from collections.abc import Callable, Iterator
from io import TextIOWrapper
from types import ModuleType
from typing import Any, Mapping, Optional, Sequence, cast

from ... import Registry
from ... import entries as talon


class ObjectShim:
    """
    A simple shim which responds to any method.
    """

    def register(self, event_code: talon.EventCode, func: Callable[..., Any]):
        registry = Registry.get_active_global_registry()
        registry.register(
            talon.Callback(
                event_code=event_code,
                function=func,
                location=talon.Location.from_function(func),
                parent_name=registry.get_active_file().name,
            )
        )

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


class TalonActionsShim:
    def __getattr__(self, name: str) -> Optional[Callable[..., Any]]:
        try:
            return cast(
                Optional[Callable[..., Any]],
                object.__getattribute__(self, name),
            )
        except AttributeError:
            registry = Registry.get_active_global_registry()
            return registry.lookup_default_function(talon.Action, name) or ObjectShim()


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


class TalonContextListsShim(Mapping[str, talon.ListValue]):
    def __init__(self, context: "TalonShim.Context"):
        self._context = context

    def _add_list_value(self, name: str, value: talon.ListValue):
        self._context._registry.register(
            talon.List(
                value=value,
                value_type_hint=None,
                name=f"{self._context._package.name}.{name}",
                description=None,
                location=self._context._context.location,
                parent_name=self._context._context.name,
                parent_type=talon.Context,
            )
        )

    def __setitem__(self, name: str, value: talon.ListValue):
        self._add_list_value(name, value)

    def update(self, values: Mapping[str, talon.ListValue]):
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

    def _add_setting_value(self, name: str, value: talon.SettingValue):
        self._context._registry.register(
            talon.Setting(
                value=value,
                value_type_hint=None,
                name=f"{self._context._package.name}.{name}",
                description=None,
                location=self._context._context.location,
                parent_name=self._context._context.name,
                parent_type=talon.Context,
            )
        )

    def __setitem__(self, name: str, value: talon.SettingValue):
        self._add_setting_value(name, value)

    def update(self, values: Mapping[str, talon.SettingValue]):
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
            self._registry = Registry.get_active_global_registry()
            self._package = self._registry.get_active_package()
            self._file = self._registry.get_active_file()
            self._module = talon.Module(
                index=len(self._file.modules) + 1,
                description=desc,
                location=self._file.location,
                parent_name=self._file.name,
            )
            self._file.modules.append(self._module.name)
            self._registry.register(self._module)

        def action_class(self, cls: type):
            for name, func in inspect.getmembers(cls, inspect.isfunction):
                assert inspect.isfunction(func)
                package = self._registry.get_active_package()
                function = talon.Function(
                    function=func,
                    location=talon.Location.from_function(func),
                    parent_name=self._module.name,
                    parent_type=talon.Module,
                )
                self._registry.register(function)
                action = talon.Action(
                    function_name=function.name,
                    function_type_hints=None,
                    name=f"{package.name}.{name}",
                    description=func.__doc__,
                    location=function.location,
                    parent_name=self._module.name,
                    parent_type=talon.Module,
                )
                self._registry.register(action)

        def action(self, name: str) -> Optional[Callable[..., Any]]:
            return (
                self._registry.lookup_default_function(talon.Action, name)
                or ObjectShim()
            )

        def capture(
            self, rule: str
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def __decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                assert inspect.isfunction(func)
                package = self._registry.get_active_package()
                function = talon.Function(
                    function=func,
                    location=talon.Location.from_function(func),
                    parent_name=self._module.name,
                    parent_type=talon.Module,
                )
                self._registry.register(function)
                capture = talon.Capture(
                    rule=talon.parse_rule(rule),
                    function_name=function.name,
                    function_type_hints=None,
                    name=f"{package.name}.{func.__name__}",
                    description=func.__doc__,
                    location=function.location,
                    parent_name=self._module.name,
                    parent_type=talon.Module,
                )
                self._registry.register(capture)
                return func

            return __decorator

        def setting(
            self,
            name: str,
            type: type,
            default: talon.SettingValue = None,
            desc: str = None,
        ):
            self._registry.register(
                talon.Setting(
                    value=default,
                    value_type_hint=type,
                    name=f"{self._package.name}.{name}",
                    description=desc,
                    location=self._module.location,
                    parent_name=self._module.name,
                    parent_type=talon.Module,
                )
            )

        def list(self, name: str, desc: str = None):
            self._registry.register(
                talon.List(
                    value=None,
                    value_type_hint=None,
                    name=f"{self._package.name}.{name}",
                    description=desc,
                    location=self._module.location,
                    parent_name=self._module.name,
                    parent_type=talon.Module,
                )
            )

        def mode(self, name: str, desc: str = None):
            self._registry.register(
                talon.Mode(
                    name=f"{self._package.name}.{name}",
                    description=desc,
                    location=self._module.location,
                    parent_name=self._module.name,
                )
            )

        def tag(self, name: str, desc: str = None):
            self._registry.register(
                talon.Tag(
                    name=f"{self._package.name}.{name}",
                    description=desc,
                    location=self._module.location,
                    parent_name=self._module.name,
                )
            )

        # TODO: apps
        # TODO: scope

    class Context(ObjectShim):
        def __init__(self, desc: Optional[str] = None):
            self._registry = Registry.get_active_global_registry()
            self._package = self._registry.get_active_package()
            self._file = self._registry.get_active_file()
            index = len(self._file.contexts) + 1
            self._context = talon.Context(
                matches=[],
                index=index,
                description=desc,
                location=self._file.location,
                parent_name=self._file.name,
            )
            self._file.contexts.append(self._context.name)
            self._registry.register(self._context)
            self._lists = TalonContextListsShim(self)
            self._settings = TalonContextSettingsShim(self)
            self._tags = TalonContextTagsShim(self)
            # TODO: matches
            # TODO: apps

        @property
        def lists(self) -> Mapping[str, talon.ListValue]:
            return self._lists

        @lists.setter
        def lists(self, lists: Mapping[str, talon.ListValue]) -> None:
            self._lists.update(lists)

        @property
        def settings(self) -> Mapping[str, talon.SettingValue]:
            return self._settings

        @settings.setter
        def settings(self, values: Mapping[str, talon.SettingValue]):
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
                    assert inspect.isfunction(func)
                    function = talon.Function(
                        function=func,
                        location=talon.Location.from_function(func),
                        parent_name=self._context.name,
                        parent_type=talon.Context,
                    )
                    self._registry.register(function)
                    action = talon.Action(
                        function_name=function.name,
                        function_type_hints=None,
                        name=f"{namespace}.{name}",
                        description=func.__doc__,
                        location=function.location,
                        parent_name=self._context.name,
                        parent_type=talon.Context,
                    )
                    self._registry.register(action)

            return __decorator

        def action(self, name: str) -> Optional[Callable[..., Any]]:
            return self._registry.lookup_default_function(talon.Action, name)

        def capture(
            self, namespace: Optional[str] = None, rule: Optional[str] = None
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            namespace = namespace or self._module_entry.get_namespace()

            def __decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                assert rule is not None
                assert inspect.isfunction(func)
                package = self._registry.get_active_package()
                function = talon.Function(
                    function=func,
                    location=talon.Location.from_function(func),
                    parent_name=self._context.name,
                    parent_type=talon.Context,
                )
                self._registry.register(function)
                capture = talon.Capture(
                    rule=talon.parse_rule(rule),
                    name=f"{package.name}.{func.__name__}",
                    function_name=function.name,
                    function_type_hints=None,
                    description=func.__doc__,
                    location=function.location,
                    parent_name=self._context.name,
                    parent_type=talon.Context,
                )
                self._registry.register(capture)
                return func

            return __decorator
