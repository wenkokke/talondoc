import inspect
import platform
from collections.abc import Callable, Iterator
from io import TextIOWrapper
from types import ModuleType
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Type,
    Union,
    cast,
    overload,
)

from tree_sitter_talon import Point

from ...._util.logging import getLogger
from ...registry import Registry, data
from ...registry.data.abc import Location

_LOGGER = getLogger(__name__)


class ObjectShim:
    """
    A simple shim which responds to any method.
    """

    def register(self, event_code: data.EventCode, func: Callable[..., Any]) -> None:
        if inspect.isfunction(func):
            registry = Registry.get_active_global_registry()
            registry.register(
                data.Callback(
                    event_code=event_code,
                    function=func,
                    location=Location.from_function(func),
                    parent_name=registry.get_active_file().name,
                )
            )
        else:
            _LOGGER.debug(
                f"skip register {data.Callback.__name__}: callback of type {func.__class__.__qualname__} is not a function"
            )

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        pass

    def __getattr__(self, name: str) -> Any:
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return self

    def __setattr__(self, name: str, value: Any) -> None:
        object.__setattr__(self, name, value)

    def __getitem__(self, name: str) -> Any:
        return self

    def __setitem__(self, name: str, value: Any) -> None:
        pass

    def __enter__(self) -> Any:
        return self

    def __exit__(self, *_args: Any) -> None:
        pass

    def __add__(self, other: Any) -> Any:
        return self

    def __sub__(self, other: Any) -> Any:
        return self

    def __mul__(self, other: Any) -> Any:
        return self

    def __pow__(self, other: Any) -> Any:
        return self

    def __mod__(self, other: Any) -> Any:
        return self

    def __floordiv__(self, other: Any) -> Any:
        return self

    def __truediv__(self, other: Any) -> Any:
        return self

    def __radd__(self, other: Any) -> Any:
        return self

    def __rsub__(self, other: Any) -> Any:
        return self

    def __rmul__(self, other: Any) -> Any:
        return self

    def __rmod__(self, other: Any) -> Any:
        return self

    def __rfloordiv__(self, other: Any) -> Any:
        return self

    def __rtruediv__(self, other: Any) -> Any:
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

    def __and__(self, other: Any) -> Any:
        return self

    def __rand__(self, other: Any) -> Any:
        return self

    def __or__(self, other: Any) -> Any:
        return self

    def __ror__(self, other: Any) -> Any:
        return self

    def __xor__(self, other: Any) -> Any:
        return self

    def __rxor__(self, other: Any) -> Any:
        return self

    def __invert__(self) -> Any:
        return self

    def __lshift__(self, other: Any) -> Any:
        return self

    def __rlshift__(self, other: Any) -> Any:
        return self

    def __rshift__(self, other: Any) -> Any:
        return self

    def __rrshift__(self, other: Any) -> Any:
        return self

    def __call__(self, *_args: Any, **_kwargs: Any) -> Any:
        return self

    def __iter__(self) -> Iterator[Any]:
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
            return registry.lookup_default_function(data.Action, name) or ObjectShim()


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


class TalonContextListsShim(Mapping[str, data.ListValue]):
    def __init__(self, context: "TalonShim.Context"):
        self._context = context

    def _add_list_value(self, name: str, value: data.ListValue) -> None:
        self._context._registry.register(
            data.List(
                value=value,
                value_type_hint=None,
                # NOTE: list names on contexts are fully qualified
                name=self._context._registry.resolve_name(
                    name, package=self._context._package
                ),
                description=None,
                location=self._context._context.location,
                parent_name=self._context._context.name,
                parent_type=data.Context,
            )
        )

    def __setitem__(self, name: str, value: data.ListValue) -> None:
        self._add_list_value(name, value)

    def update(self, values: Mapping[str, data.ListValue]) -> None:
        for name, value in values.items():
            self._add_list_value(name, value)

    def __getitem__(self, key: str) -> Union[Dict[str, Any], List[str]]:
        raise NotImplementedError()

    def __iter__(self) -> Iterator[Any]:
        raise NotImplementedError()

    def __len__(self) -> int:
        raise NotImplementedError()


class TalonContextSettingsShim(Mapping[str, data.SettingValue]):
    def __init__(self, context: "TalonShim.Context"):
        self._context = context

    def _add_setting_value(self, name: str, value: data.SettingValue) -> None:
        self._context._registry.register(
            data.Setting(
                value=value,
                value_type_hint=None,
                # NOTE: setting names on contexts are fully qualified
                name=self._context._registry.resolve_name(
                    name, package=self._context._package
                ),
                description=None,
                location=self._context._context.location,
                parent_name=self._context._context.name,
                parent_type=data.Context,
            )
        )

    def __setitem__(self, name: str, value: data.SettingValue) -> None:
        self._add_setting_value(name, value)

    def update(self, values: Mapping[str, data.SettingValue]) -> None:
        for name, value in values.items():
            self._add_setting_value(name, value)

    def __getitem__(self, key: str) -> data.SettingValue:
        raise NotImplementedError()

    def __iter__(self) -> Iterator[data.SettingValue]:
        raise NotImplementedError()

    def __len__(self) -> int:
        raise NotImplementedError()


class TalonContextTagsShim(Sequence[str]):
    def __init__(self, context: "TalonShim.Context"):
        self._context = context

    def _add_tag_import(self, name: str) -> None:
        # TODO: add use entries
        pass

    def __setitem__(self, name: str) -> None:
        self._add_tag_import(name)

    def update(self, values: Sequence[str]) -> None:
        for name in values:
            self._add_tag_import(name)

    @overload
    def __getitem__(self, index: int, /) -> str:
        ...

    @overload
    def __getitem__(self, index: slice, /) -> Sequence[str]:
        ...

    def __getitem__(self, _index: Any, /) -> Sequence[Any]:
        raise NotImplementedError()

    def __iter__(self) -> Iterator[str]:
        raise NotImplementedError()

    def __len__(self) -> int:
        raise NotImplementedError()


class TalonResourceShim(ObjectShim):
    def open(self, file: str, mode: str = "r") -> TextIOWrapper:
        return cast(TextIOWrapper, open(file, mode))

    def read(self, file: str) -> str:
        raise NotImplementedError()

    def write(self, _file: str, _contents: str) -> str:
        raise NotImplementedError()


class TalonShim(ModuleShim):
    """
    A shim for the 'talon' module.
    """

    def __init__(self) -> None:
        super().__init__("talon")
        self.actions = TalonActionsShim()
        self.app = TalonAppShim()
        self.resource = TalonResourceShim()
        # TODO: app
        # TODO: ui

    class Module(ObjectShim):
        def __init__(self, desc: Optional[str] = None) -> None:
            self._registry = Registry.get_active_global_registry()
            self._package = self._registry.get_active_package()
            self._file = self._registry.get_active_file()
            self._module = data.Module(
                index=len(self._file.modules),
                description=desc,
                location=self._file.location,
                parent_name=self._file.name,
            )
            self._file.modules.append(self._module.name)
            self._registry.register(self._module)

        def action_class(self, cls: Type[Any]) -> Type[Any]:
            for name, func in inspect.getmembers(cls, inspect.isfunction):
                assert callable(func)
                package = self._registry.get_active_package()
                function = data.Function(
                    namespace=package.name,
                    function=func,
                    location=Location.from_function(func),
                    parent_name=self._module.name,
                    parent_type=data.Module,
                )
                self._registry.register(function)
                action = data.Action(
                    function_name=function.name,
                    function_signature=inspect.signature(func),
                    name=f"{package.name}.{name}",
                    description=func.__doc__,
                    location=function.location,
                    parent_name=self._module.name,
                    parent_type=data.Module,
                )
                self._registry.register(action)
            return cls

        def action(self, name: str) -> Optional[Callable[..., Any]]:
            function = self._registry.lookup_default_function(data.Action, name)
            return function or ObjectShim()

        def capture(
            self, rule: str
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def __decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                assert callable(func)
                package = self._registry.get_active_package()
                function = data.Function(
                    namespace=package.name,
                    function=func,
                    location=Location.from_function(func),
                    parent_name=self._module.name,
                    parent_type=data.Module,
                )
                self._registry.register(function)
                capture = data.Capture(
                    rule=data.parse_rule(rule),
                    function_name=function.name,
                    function_signature=inspect.signature(func),
                    name=f"{package.name}.{func.__name__}",
                    description=func.__doc__,
                    location=function.location,
                    parent_name=self._module.name,
                    parent_type=data.Module,
                )
                self._registry.register(capture)
                return func

            return __decorator

        def setting(
            self,
            name: str,
            type: type,
            default: data.SettingValue = None,
            desc: Optional[str] = None,
        ) -> None:
            self._registry.register(
                data.Setting(
                    value=default,
                    value_type_hint=type,
                    # NOTE: list names passed to modules are unqualified
                    name=f"{self._package.name}.{name}",
                    description=desc,
                    location=self._module.location,
                    parent_name=self._module.name,
                    parent_type=data.Module,
                )
            )

        def list(
            self,
            name: str,
            desc: Optional[str] = None,
        ) -> None:
            self._registry.register(
                data.List(
                    value=None,
                    value_type_hint=None,
                    # NOTE: list names passed to modules are unqualified
                    name=f"{self._package.name}.{name}",
                    description=desc,
                    location=self._module.location,
                    parent_name=self._module.name,
                    parent_type=data.Module,
                )
            )

        def mode(
            self,
            name: str,
            desc: Optional[str] = None,
        ) -> None:
            self._registry.register(
                data.Mode(
                    name=f"{self._package.name}.{name}",
                    description=desc,
                    location=self._module.location,
                    parent_name=self._module.name,
                )
            )

        def tag(
            self,
            name: str,
            desc: Optional[str] = None,
        ) -> None:
            self._registry.register(
                data.Tag(
                    name=f"{self._package.name}.{name}",
                    description=desc,
                    location=self._module.location,
                    parent_name=self._module.name,
                )
            )

        # TODO: apps
        # TODO: scope

    class Context(ObjectShim):
        def __init__(self, desc: Optional[str] = None) -> None:
            self._registry = Registry.get_active_global_registry()
            self._package = self._registry.get_active_package()
            self._file = self._registry.get_active_file()
            self._context = data.Context(
                matches=[],
                index=len(self._file.contexts),
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
        def lists(self) -> Mapping[str, data.ListValue]:
            return self._lists

        @lists.setter
        def lists(self, lists: Mapping[str, data.ListValue]) -> None:
            self._lists.update(lists)

        @property
        def settings(self) -> Mapping[str, data.SettingValue]:
            return self._settings

        @settings.setter
        def settings(self, values: Mapping[str, data.SettingValue]) -> None:
            self._settings.update(values)

        @property
        def tags(self) -> Sequence[str]:
            return self._tags

        @tags.setter
        def tags(self, values: Sequence[str]) -> None:
            self._tags.update(values)

        def action_class(self, namespace: str) -> Callable[[Type[Any]], Type[Any]]:
            def __decorator(cls: Type[Any]) -> Type[Any]:
                for name, func in inspect.getmembers(cls, inspect.isfunction):
                    # LINT: check if function on decorated class is a function
                    assert callable(func)

                    location = Location.from_function(func)
                    function = data.Function(
                        namespace=namespace,
                        function=func,
                        location=location,
                        parent_name=self._context.name,
                        parent_type=data.Context,
                    )
                    self._registry.register(function)
                    action = data.Action(
                        function_name=function.name,
                        function_signature=inspect.signature(func),
                        # NOTE: function names on action classes are unqualified
                        name=f"{namespace}.{name}",
                        description=func.__doc__,
                        location=location,
                        parent_name=self._context.name,
                        parent_type=data.Context,
                    )
                    self._registry.register(action)
                return cls

            return __decorator

        def action(
            self, name: str
        ) -> Optional[Callable[[Callable[..., Any]], Callable[..., Any]]]:
            def __decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                # LINT: check if function on decorated class is a function
                assert callable(func)
                namespace = name.split(".")[0]

                location = Location.from_function(func)
                function = data.Function(
                    namespace=namespace,
                    function=func,
                    location=location,
                    parent_name=self._context.name,
                    parent_type=data.Context,
                )
                self._registry.register(function)
                action = data.Action(
                    function_name=function.name,
                    function_signature=inspect.signature(func),
                    # NOTE: function names on actions are fully qualified
                    name=name,
                    description=func.__doc__,
                    location=location,
                    parent_name=self._context.name,
                    parent_type=data.Context,
                )
                self._registry.register(action)
                return func

            return __decorator

        def capture(
            self, name: Optional[str] = None, rule: Optional[str] = None
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def __decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                # LINT: check if decorated function is a function
                if not inspect.isfunction(func):
                    _LOGGER.error(f"decorated object is not a function")
                    return func

                location = Location.from_function(func)

                # LINT: check if rule is set
                if rule is None:
                    _LOGGER.error(f"missing capture rule at {location}")
                    # insert placeholder rule
                    parsed_rule = data.Rule(
                        text="",
                        type_name="rule",
                        start_position=Point(-1, -1),
                        end_position=Point(-1, -1),
                        children=[],
                    )
                else:
                    parsed_rule = data.parse_rule(rule)

                # LINT: resolve capture name and check if decorated function has expected name
                if name is not None:
                    exp_funcname = name.split(".")[-1]
                    act_funcname = func.__name__
                    # TODO: only issue warning if linter is pedanic
                    if exp_funcname != act_funcname:
                        _LOGGER.warning(
                            f"function for capture {name} "
                            f"at {location} "
                            f"is named {act_funcname} "
                            f"instead of {exp_funcname}"
                        )
                    resolved_name = self._registry.resolve_name(name)
                else:
                    _LOGGER.error(
                        f"missing name for capture decorator "
                        f"applied to {func.__name__} "
                        f"at {location}"
                    )
                    resolved_name = f"{self._package.name}.{func.__name__}"

                function = data.Function(
                    namespace=resolved_name,
                    function=func,
                    location=location,
                    parent_name=self._context.name,
                    parent_type=data.Context,
                )
                self._registry.register(function)
                capture = data.Capture(
                    rule=parsed_rule,
                    # NOTE: capture names passed to contexts are fully qualified
                    name=resolved_name,
                    function_name=function.name,
                    function_signature=None,
                    description=func.__doc__,
                    location=location,
                    parent_name=self._context.name,
                    parent_type=data.Context,
                )
                self._registry.register(capture)
                return func

            return __decorator
