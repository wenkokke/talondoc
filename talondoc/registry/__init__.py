from dataclasses import dataclass
from functools import singledispatchmethod
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Union,
    overload,
)

from typing_extensions import Final

from ..util.logging import getLogger
from . import entries as talon
from .entries import Group, GroupDataVar, SimpleDataVar

_LOGGER = getLogger(__name__)


@dataclass(init=False)
class Registry:
    _data: Final[Dict[str, Any]]
    _temp_data: Final[Dict[str, Any]]

    _active_package: Optional[talon.Package] = None
    _active_file: Optional[talon.File] = None

    def __init__(self, data: Dict[str, Any], temp_data: Dict[str, Any]):
        self._data = data
        self._temp_data = temp_data
        self._active_package = None
        self._active_file = None

    ######################################################################
    # Register Data
    ######################################################################

    @singledispatchmethod
    def register(self, value: object) -> None:
        raise TypeError(type(value))

    def _register_simple_data(self, value: SimpleDataVar) -> None:
        # Print the value name to the log.
        _LOGGER.info(f"register {value.__class__.__name__} {value.name}")
        # Register the data in the store.
        store = self._typed_store(value.__class__)
        old_value = store.get(value.name, None)
        if old_value is not None:
            raise talon.DuplicateData(value, old_value)
        store[value.name] = value
        # Set the active package, file, module, or context.
        if isinstance(value, talon.Package):
            self._active_package = value
        if isinstance(value, talon.File):
            self._active_file = value

    def _register_grouped_data(self, value: GroupDataVar) -> None:
        # Print the value name to the log.
        _LOGGER.info(f"register {value.__class__.__name__} {value.name}")
        # Register the data in the store.
        store = self._typed_store(value.__class__)
        old_group = store.get(value.name)
        if old_group is None:
            store[value.name] = old_group = Group[GroupDataVar]()
        old_group.append(value)

    def _register_callback(self, value: talon.Callback) -> None:
        # Print the value name to the log.
        _LOGGER.info(f"register {value.__class__.__name__} {value.name}")
        # Register the data in the store.
        self._typed_store(talon.Callback).setdefault(value.event_code, []).append(value)

    # Simple entries
    register.register(talon.Package, _register_simple_data)
    register.register(talon.File, _register_simple_data)
    register.register(talon.Function, _register_simple_data)
    register.register(talon.Module, _register_simple_data)
    register.register(talon.Context, _register_simple_data)
    register.register(talon.Command, _register_simple_data)
    register.register(talon.Mode, _register_simple_data)
    register.register(talon.Tag, _register_simple_data)

    # Group entries
    register.register(talon.Action, _register_grouped_data)
    register.register(talon.Capture, _register_grouped_data)
    register.register(talon.List, _register_grouped_data)
    register.register(talon.Setting, _register_grouped_data)

    # Callback entries
    register.register(talon.Callback, _register_callback)

    ######################################################################
    # Look Up Data
    ######################################################################

    @overload
    def lookup(
        self,
        cls: type[SimpleDataVar],
        name: str,
    ) -> Optional[SimpleDataVar]:
        ...

    @overload
    def lookup(
        self,
        cls: type[GroupDataVar],
        name: str,
    ) -> Optional[Group[GroupDataVar]]:
        ...

    @overload
    def lookup(
        self,
        cls: type[talon.Callback],
        name: talon.EventCode,
    ) -> Optional[Sequence[talon.Callback]]:
        ...

    def lookup(self, cls: type[talon.Data], name: Any) -> Optional[Any]:
        return self._typed_store(cls).get(self._resolve_name(name), None)

    def lookup_description(self, cls: type[talon.Data], name: Any) -> Optional[str]:
        if talon.is_simple(cls):
            simple = self.lookup(cls, name)
            if simple:
                return simple.description
        if talon.is_group(cls):
            group = self.lookup_default(cls, name)  # type: ignore
            if group:
                return group.description
        return None

    def lookup_default(
        self, cls: type[GroupDataVar], name: str
    ) -> Optional[GroupDataVar]:
        group = self.lookup(cls, name)
        if group:
            for declaration in group.declarations:
                return declaration
            for override in group.overrides:
                assert override.parent_type == "context"
                context = self.lookup(talon.Context, override.parent_name)
                if context and context.is_default():
                    return override
        return None

    def lookup_default_function(
        self, cls: type[Union[talon.Action, talon.Capture]], name: str
    ) -> Optional[Callable[..., Any]]:
        action = self.lookup_default(talon.Action, name)
        if action and action.function_name:
            action_function = self.lookup(talon.Function, action.function_name)
            if action_function:
                return action_function.function
        return None

    def _resolve_name(self, name: str) -> str:
        try:
            package = self.get_active_package()
            parts = name.split(".")
            if len(parts) >= 1 and parts[0] == "self":
                name = ".".join((package.name, *parts[1:]))
        except NoActivePackage:
            pass
        return name

    ######################################################################
    # Typed Access To Data
    ######################################################################

    @property
    def packages(self) -> Mapping[str, talon.Package]:
        return self._typed_store(talon.Package)

    @property
    def files(self) -> Mapping[str, talon.File]:
        return self._typed_store(talon.File)

    @property
    def functions(self) -> Mapping[str, talon.Function]:
        return self._typed_store(talon.Function)

    @property
    def callbacks(self) -> Mapping[talon.EventCode, Sequence[talon.Callback]]:
        return self._typed_store(talon.Callback)

    @property
    def modules(self) -> Mapping[str, talon.Module]:
        return self._typed_store(talon.Module)

    @property
    def contexts(self) -> Mapping[str, talon.Context]:
        return self._typed_store(talon.Context)

    @property
    def commands(self) -> Mapping[str, talon.Command]:
        return self._typed_store(talon.Command)

    @property
    def actions(self) -> Mapping[str, Group[talon.Action]]:
        return self._typed_store(talon.Action)

    @property
    def captures(self) -> Mapping[str, Group[talon.Capture]]:
        return self._typed_store(talon.Capture)

    @property
    def lists(self) -> Mapping[str, Group[talon.List]]:
        return self._typed_store(talon.List)

    @property
    def settings(self) -> Mapping[str, Group[talon.Setting]]:
        return self._typed_store(talon.Setting)

    @property
    def modes(self) -> Mapping[str, talon.Mode]:
        return self._typed_store(talon.Mode)

    @property
    def tags(self) -> Mapping[str, talon.Tag]:
        return self._typed_store(talon.Tag)

    ######################################################################
    # Internal Typed Access To Data
    ######################################################################

    @overload
    def _typed_store(self, cls: type[SimpleDataVar]) -> Dict[str, SimpleDataVar]:
        ...

    @overload
    def _typed_store(self, cls: type[GroupDataVar]) -> Dict[str, Group[GroupDataVar]]:
        ...

    @overload
    def _typed_store(
        self, cls: type[talon.Callback]
    ) -> Dict[talon.EventCode, List[talon.Callback]]:
        ...

    @overload
    def _typed_store(self, cls: type[talon.Data]) -> Dict[Any, Any]:
        ...

    def _typed_store(self, cls: type[talon.Data]) -> Dict[Any, Any]:
        # If the data is not serialisable, store it in temp_data:
        if cls.is_serialisable():
            data = self._data
        else:
            data = self._temp_data
        # Store the data in a dictionary indexed by its type name.
        store = data.setdefault(cls.__name__, {})
        assert isinstance(store, dict)
        return store

    ##################################################
    # The active GLOBAL registry
    ##################################################

    _active_global_registry: ClassVar[Optional["Registry"]]

    @staticmethod
    def get_active_global_registry() -> "Registry":
        try:
            if Registry._active_global_registry:
                return Registry._active_global_registry
        except AttributeError:
            pass
        raise NoActiveRegistry()

    def activate(self: "Registry"):
        """
        Activate this registry.
        """
        Registry._active_global_registry = self

    def deactivate(self: "Registry"):
        """
        Deactivate this registry.
        """
        if self is not None:
            assert self == Registry._active_global_registry
        Registry._active_global_registry = None

    ##################################################
    # The active package, file, module, or context
    ##################################################

    @staticmethod
    def get_active_package() -> talon.Package:
        """
        Retrieve the active package.
        """
        registry = Registry.get_active_global_registry()
        try:
            if registry._active_package is not None:
                return registry._active_package
        except AttributeError:
            pass
        raise NoActivePackage()

    @staticmethod
    def get_active_file() -> talon.File:
        """
        Retrieve the active file.
        """
        registry = Registry.get_active_global_registry()
        try:
            if registry._active_file is not None:
                return registry._active_file
        except AttributeError:
            pass
        raise NoActiveFile()


##############################################################################
# Exceptions
##############################################################################


class NoActiveRegistry(Exception):
    """
    Exception raised when the user attempts to load a talon module
    outside of the 'talon_shims' context manager.
    """

    def __str__(self) -> str:
        return "No active registry"


class NoActivePackage(Exception):
    """
    Exception raised when the user attempts to get the active package
    when no package is being processed.
    """

    def __str__(self) -> str:
        return "No active package"


class NoActiveFile(Exception):
    """
    Exception raised when the user attempts to get the active file
    when no file is being processed.
    """

    def __str__(self) -> str:
        return "No active file"
