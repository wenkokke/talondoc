import inspect
from collections.abc import Callable
from typing import Any, Mapping, Optional, Sequence, Union

from ..analyze.registry import Registry
from ..entries import (
    ActionEntry,
    ActionGroupEntry,
    CaptureEntry,
    ContextEntry,
    ListEntry,
    ListValue,
    ModeEntry,
    ModuleEntry,
    PythonFileEntry,
    SettingEntry,
    SettingValue,
    TagEntry,
)
from .core import (
    ModuleShim,
    ObjectShim,
    TalonActionsShim,
    TalonAppShim,
    TalonContextListsShim,
    TalonContextSettingsShim,
    TalonContextTagsShim,
    TalonResourceShim,
    action,
)


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
            file = Registry.activefile()
            assert isinstance(file, PythonFileEntry)
            self._module_entry = ModuleEntry(file=file, desc=desc)
            Registry.active().register(self._module_entry)

        def action_class(self, cls: type):
            for name, func in inspect.getmembers(cls, inspect.isfunction):
                name = f"{self._module_entry.namespace}.{name}"
                action_entry = ActionEntry(
                    module=self._module_entry, name=name, func=func
                )
                Registry.active().register(action_entry)

        def action(self, name: str) -> Optional[Callable[..., Any]]:
            registry = Registry.active()
            namespace = self._module_entry.namespace
            return action(registry, name, namespace=namespace)

        def capture(
            self, rule: str
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def __decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                namespace = self._module_entry.namespace
                capture_entry = CaptureEntry(
                    name=f"{namespace}.{func.__name__}",
                    module=self._module_entry,
                    rule=rule,
                    func=func,
                )
                Registry.active().register(capture_entry)
                return func

            return __decorator

        def setting(
            self,
            name: str,
            type: type,
            default: Any = None,
            desc: str = None,
        ):
            namespace = self._module_entry.namespace
            setting_entry = SettingEntry(
                name=f"{namespace}.{name}",
                module=self._module_entry,
                type=type,
                desc=desc,
                default=default,
            )
            Registry.active().register(setting_entry)

        def list(self, name: str, desc: str = None):
            namespace = self._module_entry.namespace
            list_entry = ListEntry(
                name=f"{namespace}.{name}",
                module=self._module_entry,
                desc=desc,
            )
            Registry.active().register(list_entry)

        def mode(self, name: str, desc: str = None):
            namespace = self._module_entry.namespace
            mode_entry = ModeEntry(
                name=f"{namespace}.{name}",
                module=self._module_entry,
                desc=desc,
            )
            Registry.active().register(mode_entry)

        def tag(self, name: str, desc: str = None):
            namespace = self._module_entry.namespace
            tag_entry = TagEntry(
                name=f"{namespace}.{name}",
                module=self._module_entry,
                desc=desc,
            )
            Registry.active().register(tag_entry)

        # TODO: apps
        # TODO: scope

    class Context(ObjectShim):
        def __init__(self, desc: Optional[str] = None):
            file = Registry.activefile()
            assert isinstance(file, PythonFileEntry)
            self._module_entry = ContextEntry(file=file, desc=desc)
            Registry.active().register(self._module_entry)
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
                    name = f"{namespace}.{name}"
                    action_entry = ActionEntry(
                        module=self._module_entry, name=name, func=func
                    )
                    Registry.active().register(action_entry)

            return __decorator

        def action(self, name: str) -> Optional[Callable[..., Any]]:
            registry = Registry.active()
            namespace = self._module_entry.namespace
            return action(registry, name, namespace=namespace)

        def capture(
            self, namespace: Optional[str] = None, rule: Optional[str] = None
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            namespace = namespace or self._module_entry.namespace

            def __decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                if rule is None:
                    raise ValueError("Missing rule")

                capture_entry = CaptureEntry(
                    name=f"{namespace}.{func.__name__}",
                    module=self._module_entry,
                    rule=rule,
                    func=func,
                )
                Registry.active().register(capture_entry)
                return func

            return __decorator
