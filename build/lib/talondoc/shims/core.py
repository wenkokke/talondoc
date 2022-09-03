import platform
import sys
import types
from collections.abc import Callable, Iterator
from io import TextIOWrapper
from typing import TYPE_CHECKING, Any, Mapping, Optional, Sequence, cast

from ..analyze.registry import Registry
from ..entries import (
    ActionGroupEntry,
    CallbackEntry,
    EventCode,
    ListValue,
    ListValueEntry,
    SettingValue,
    SettingValueEntry,
    TagImportEntry,
    resolve_name,
)

if TYPE_CHECKING:
    from .talon import TalonShim

    Context = TalonShim.Context
else:
    Context = Any


class ObjectShim:
    """
    A simple shim which responds to any method.
    """

    def register(self, event_code: EventCode, callback: Callable[..., Any]):
        file = Registry.activefile()
        callback_entry = CallbackEntry(
            event_code=event_code, callback=callback, file=file
        )
        Registry.active().register(callback_entry)

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


class ModuleShim(types.ModuleType):
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


def action(
    registry: Registry, name: str, *, namespace: Optional[str] = None
) -> Optional[Callable[..., Any]]:
    resolved_name = resolve_name(name, namespace=namespace)
    qualified_name = f"action-group:{resolved_name}"
    action_group_entry = registry.lookup(qualified_name)
    if isinstance(action_group_entry, ActionGroupEntry):
        if action_group_entry.default:
            return action_group_entry.default.func
    return ObjectShim()


class TalonActionsShim:
    def __getattr__(self, name: str) -> Optional[Callable[..., Any]]:
        try:
            return cast(
                Optional[Callable[..., Any]],
                object.__getattribute__(self, name),
            )
        except AttributeError:
            registry = Registry.active()
            file = registry.currentfile
            namespace = file.namespace if file else None
            return action(registry, name, namespace=namespace)


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


class TalonContextTagsShim(Sequence):
    def __init__(self, context: Context):
        self._context = context

    def _add_tag_import(self, name: str):
        namespace = self._context._module_entry.namespace
        tag_import_entry = TagImportEntry(
            name=f"{namespace}.{name}",
            file_or_module=self._context._module_entry,
        )
        Registry.active().register(tag_import_entry)

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
