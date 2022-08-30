import inspect
import types
import typing
from ..analyze.registry import Registry
from ..types import ActionEntry, ModuleEntry
from .core import ObjectShim, ModuleShim


class TalonShim(ModuleShim):
    """
    A shim for the 'talon' module.
    """

    def __init__(self):
        super().__init__("talon")

    class Module(ObjectShim):
        def __init__(self, desc: typing.Optional[str] = None):
            self._module_entry = ModuleEntry(file=Registry.activefile(), desc=desc)
            self._module_entry.file.modules.append(self._module_entry)
            Registry.active().register(self._module_entry)

        def action_class(self, cls: type):
            for name, func in inspect.getmembers(cls, inspect.isfunction):
                name = f"{self._module_entry.namespace}.{name}"
                action_entry = ActionEntry(
                    module=self._module_entry, name=name, func=func
                )
                Registry.active().register(action_entry)
