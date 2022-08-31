from collections.abc import Callable, Iterator
import types
from typing import Any, Mapping, Optional, TYPE_CHECKING
from ..types import (
    ActionEntry,
    ListValue,
    ListValueEntry,
    SettingValue,
    SettingValueEntry,
    resolve_name,
)
from ..analyze.registry import Registry


class ObjectShim:
    """
    A simple shim which responds to any method.
    """

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


class ModuleShim(types.ModuleType, ObjectShim):
    """
    A module shim which defines any value.
    """

    def __init__(self, fullname: str):
        super().__init__(fullname)


def action(
    registry: Registry, name: str, *, namespace: Optional[str] = None
) -> Optional[Callable[..., Any]]:
    resolved_name = resolve_name(name, namespace=namespace)
    qualified_name = f"action:{resolved_name}"
    action_entry = registry.lookup(qualified_name)
    if isinstance(action_entry, ActionEntry):
        return action_entry.func
    else:

        def __action_shim(*args, **kwargs):
            return ObjectShim(*args, **kwargs)

        return __action_shim


class TalonActionsShim:
    def __getattr__(self, name: str) -> Optional[Callable[..., Any]]:
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            registry = Registry.active()
            file = registry.get_latest_file()
            namespace = file.namespace if file else None
            return action(registry, name, namespace=namespace)


if TYPE_CHECKING:
    from .talon import TalonShim

    Context = TalonShim.Context
else:
    Context = Any


class TalonContextListsShim(Mapping[str, ListValue]):
    def __init__(self, context: Context):
        self._context = context

    def _add_list_value(self, name: str, value: ListValue):
        namespace = self._context._module_entry.namespace
        list_entry = ListValueEntry(
            name=f"{namespace}.{name}",
            module=self._context._module_entry,
            value=value,
        )
        Registry.active().register(list_entry)

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
    def __init__(self, context: Context):
        self._context = context

    def _add_setting_value(self, name: str, value: SettingValue):
        namespace = self._context._module_entry.namespace
        setting_entry = SettingValueEntry(
            name=f"{namespace}.{name}",
            file_or_module=self._context._module_entry,
            value=value,
        )
        Registry.active().register(setting_entry)

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
