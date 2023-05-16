import inspect
import itertools
from dataclasses import dataclass
from functools import singledispatchmethod
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Union,
    cast,
    overload,
)

from more_itertools import partition
from talonfmt import talonfmt
from typing_extensions import Final

from talondoc.analysis.registry.entries.serialise import JsonValue

from ..._util.logging import getLogger
from . import entries as talon
from .entries import CallbackVar
from .entries.abc import (
    Data,
    DataVar,
    DuplicateData,
    GroupData,
    GroupDataHasFunction,
    GroupDataVar,
    SimpleData,
    SimpleDataVar,
    UnknownReference,
)

_LOGGER = getLogger(__name__)


@dataclass
class Registry:
    _data: Final[Dict[str, Any]]
    _temp_data: Final[Dict[str, Any]]

    _active_package: Optional[talon.Package] = None
    _active_file: Optional[talon.File] = None

    def __init__(
        self,
        *,
        data: Dict[str, Any] = {},
        temp_data: Dict[str, Any] = {},
        continue_on_error: bool = True,
    ):
        self._data = data
        self._temp_data = temp_data
        self._active_package = None
        self._active_file = None
        self._continue_on_error = continue_on_error

    ######################################################################
    # Register Data
    ######################################################################

    @singledispatchmethod
    def register(self, value: DataVar) -> DataVar:
        raise TypeError(type(value))

    def _register_simple_data(self, value: SimpleDataVar) -> SimpleDataVar:
        # Print the value name to the log.
        _LOGGER.debug(f"register {value.__class__.__name__} {value.name}")
        # Register the data in the store.
        store = self._typed_store(value.__class__)
        old_value = store.get(value.name, None)
        if old_value is not None:
            exc = DuplicateData([value, old_value])
            if self._continue_on_error:
                _LOGGER.warning(exc)
                return old_value
            else:
                raise exc
        store[value.name] = value
        # Set the active package, file, module, or context.
        if isinstance(value, talon.Package):
            self._active_package = value
        if isinstance(value, talon.File):
            self._active_file = value
        return value

    def _register_grouped_data(self, value: GroupDataVar) -> GroupDataVar:
        # Print the value name to the log.
        _LOGGER.debug(f"register {value.__class__.__name__} {value.name}")
        # Register the data in the store.
        store = self._typed_store(value.__class__)
        store.setdefault(value.name, []).append(value)
        return value

    def _register_callback(self, value: CallbackVar) -> CallbackVar:
        # Print the value name to the log.
        _LOGGER.debug(f"register {value.__class__.__name__} {value.name}")
        # Register the data in the store.
        self._typed_store(talon.Callback).setdefault(value.event_code, []).append(value)
        return value

    # Simple entries
    register.register(talon.Package, _register_simple_data)
    register.register(talon.File, _register_simple_data)
    register.register(talon.Function, _register_simple_data)
    register.register(talon.Module, _register_simple_data)
    register.register(talon.Context, _register_simple_data)
    register.register(talon.Mode, _register_simple_data)
    register.register(talon.Tag, _register_simple_data)

    # Group entries
    register.register(talon.Command, _register_grouped_data)
    register.register(talon.Action, _register_grouped_data)
    register.register(talon.Capture, _register_grouped_data)
    register.register(talon.List, _register_grouped_data)
    register.register(talon.Setting, _register_grouped_data)

    # Callback entries
    register.register(talon.Callback, _register_callback)

    def extend(self, values: Sequence[DataVar]) -> None:
        for value in values:
            self.register(value)

    ######################################################################
    # Finding Data
    ######################################################################

    def resolve_packages(
        self, packages: Iterator[Union[talon.PackageName, talon.Package]]
    ) -> Iterator[talon.Package]:
        for package in packages:
            if isinstance(package, talon.Package):
                yield package
            else:
                try:
                    yield self.get(talon.Package, package)
                except UnknownReference as e:
                    _LOGGER.error(e)
                    pass

    def resolve_files(
        self, files: Iterator[Union[talon.FileName, talon.File]]
    ) -> Iterator[talon.File]:
        for file in files:
            if isinstance(file, talon.File):
                yield file
            else:
                try:
                    yield self.get(talon.File, file)
                except UnknownReference as e:
                    _LOGGER.error(e)
                    pass

    def resolve_contexts(
        self, contexts: Iterator[Union[talon.FileName, talon.File, talon.Context]]
    ) -> Iterator[talon.Context]:
        for value in contexts:
            if isinstance(value, talon.Context):
                yield value
            else:
                if isinstance(value, str):
                    try:
                        value = self.get(talon.File, value)
                    except UnknownReference as e:
                        _LOGGER.error(e)
                        continue
                assert isinstance(value, talon.File)
                for context_name in value.contexts:
                    yield self.get(talon.Context, context_name, referenced_by=value)

    def get_commands(
        self,
        *,
        restrict_to: Optional[
            Iterator[Union[talon.FileName, talon.File, talon.Context]]
        ] = None,
    ) -> Iterator[talon.Command]:
        if restrict_to is None:
            for group in self.commands.values():
                assert isinstance(group, list), f"Unexpected value {group}"
                for command in group:
                    yield command
        else:
            for context in self.resolve_contexts(restrict_to):
                for command_name in context.commands:
                    yield self.get(talon.Command, command_name, referenced_by=context)

    def find_commands(
        self,
        text: Sequence[str],
        *,
        fullmatch: bool = False,
        restrict_to: Optional[Iterator[Union[talon.FileName, talon.Context]]] = None,
    ) -> Iterator[talon.Command]:
        for command in self.get_commands(restrict_to=restrict_to):
            if self.match(text, command.rule, fullmatch=fullmatch):
                yield command

    def match(
        self,
        text: Sequence[str],
        rule: talon.Rule,
        *,
        fullmatch: bool = False,
    ) -> bool:
        try:
            if rule.match(
                text,
                fullmatch=fullmatch,
                get_capture=self._get_capture_rule,
                get_list=self._get_list_value,
            ):
                return True
        except IndexError as e:
            _LOGGER.warning(
                f"Caught {e.__class__.__name__} "
                f"when deciding if '{talonfmt(rule)}' "
                f"matches '{' '.join(text)}'"
            )
        return False

    # TODO: remove once builtins are properly supported
    _BUILTIN_CAPTURE_NAMES: ClassVar[Sequence[talon.CaptureName]] = (
        "digit_string",
        "digits",
        "number",
        "number_signed",
        "number_small",
        "phrase",
        "word",
    )

    def _get_capture_rule(self, name: talon.CaptureName) -> Optional[talon.Rule]:
        """Get the rule for a capture. Hook for 'match'."""
        try:
            return self.get(talon.Capture, name).rule
        except UnknownReference as e:
            # If the capture is not a builtin capture, log a warning:
            if name not in self.__class__._BUILTIN_CAPTURE_NAMES:
                _LOGGER.warning(e)
            return None

    def _get_list_value(self, name: talon.ListName) -> Optional[talon.ListValue]:
        """Get the values for a list. Hook for 'match'."""
        try:
            return self.get(talon.List, name).value
        except UnknownReference as e:
            _LOGGER.warning(e)
            return None

    ######################################################################
    # Look Up Data
    ######################################################################

    def get(
        self,
        cls: type[DataVar],
        name: str,
        *,
        referenced_by: Optional[Data] = None,
    ) -> DataVar:
        value: Optional[DataVar] = None
        if issubclass(cls, SimpleData):
            value = cast(Optional[DataVar], self.lookup(cls, name))
            # For files, try various alternatives:
            if value is None and issubclass(cls, talon.File):
                value = cast(
                    Optional[DataVar],
                    # Try the search again with ".talon" suffixed:
                    self.lookup(cls, f"{name}.talon") or
                    # Try the search again assuming name is a path:
                    self.lookup(cls, f"user.{name.replace('/', '.')}"),
                )

        elif issubclass(cls, GroupData):
            value = cast(Optional[DataVar], self.lookup_default(cls, name))
        elif issubclass(cls, talon.Callback):
            raise ValueError(f"Registry.get does not support callbacks")
        if value is not None:
            return value
        else:
            raise UnknownReference(
                cls,
                name,
                referenced_by=referenced_by,
                known_references=tuple(self._typed_store(cls).keys()),
            )

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
    ) -> Optional[List[GroupDataVar]]:
        ...

    @overload
    def lookup(
        self,
        cls: type[talon.Callback],
        name: talon.EventCode,
    ) -> Optional[Sequence[talon.Callback]]:
        ...

    def lookup(self, cls: type[Data], name: Any) -> Optional[Any]:
        return self._typed_store(cls).get(self.resolve_name(name), None)

    def lookup_description(self, cls: type[Data], name: Any) -> Optional[str]:
        if issubclass(cls, SimpleData):
            simple = self.lookup(cls, name)
            if simple:
                return simple.description
        if issubclass(cls, GroupData):
            group = self.lookup_default(cls, name)
            if group:
                return group.description
        return None

    def lookup_default(
        self, cls: type[GroupDataVar], name: str
    ) -> Optional[GroupDataVar]:
        group = self.lookup(cls, name)
        if group:
            _IS_DECLARATION: int = 0
            _IS_ALWAYS_ON: int = 1

            def _complexity(obj: GroupDataVar) -> int:
                if issubclass(obj.parent_type, talon.Module):
                    return _IS_DECLARATION
                else:
                    ctx = self.get(talon.Context, obj.parent_name, referenced_by=obj)
                    return _IS_ALWAYS_ON + len(ctx.matches)

            sorted_group = [(_complexity(obj), obj) for obj in group]
            sorted_group.sort(key=lambda tup: tup[0])
            declarations = [obj for c, obj in sorted_group if c == _IS_DECLARATION]
            if len(declarations) >= 2:
                _LOGGER.warning(DuplicateData(declarations))
            return sorted_group[0][1]
        return None

    def lookup_default_function(
        self, cls: type[GroupDataHasFunction], name: str
    ) -> Optional[Callable[..., Any]]:
        value = self.lookup_default(cls, name)
        if value and value.function_name:
            function = self.lookup(talon.Function, value.function_name)
            if function is not None:
                # Create copy for _function_wrapper
                func = function.function

                def _function_wrapper(*args: Any, **kwargs: Any) -> Any:
                    func_name = func.__name__
                    func_type = inspect.signature(func)
                    act_argc = len(args) + len(kwargs)
                    exp_argc = len(func_type.parameters)
                    if act_argc != exp_argc:
                        act_argv: List[str] = []
                        act_argv.extend(map(str, args))
                        act_argv.extend(f"{key}={val}" for key, val in kwargs.items())
                        _LOGGER.warning(
                            f"mismatch in number of parameters for {func_name}\n"
                            f"expected: {func_type}\n"
                            f"found: ({', '.join(act_argv)})"
                        )
                    return func(*args, **kwargs)

                return _function_wrapper
            else:
                return None
        return None

    def resolve_name(
        self, name: str, *, package: Optional[talon.Package] = None
    ) -> str:
        try:
            if package is None:
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
    def callbacks(self) -> Mapping[talon.EventCode, List[talon.Callback]]:
        return self._typed_store(talon.Callback)

    @property
    def modules(self) -> Mapping[str, talon.Module]:
        return self._typed_store(talon.Module)

    @property
    def contexts(self) -> Mapping[str, talon.Context]:
        return self._typed_store(talon.Context)

    @property
    def commands(self) -> Mapping[str, List[talon.Command]]:
        return self._typed_store(talon.Command)

    @property
    def actions(self) -> Mapping[str, List[talon.Action]]:
        return self._typed_store(talon.Action)

    @property
    def captures(self) -> Mapping[str, List[talon.Capture]]:
        return self._typed_store(talon.Capture)

    @property
    def lists(self) -> Mapping[str, List[talon.List]]:
        return self._typed_store(talon.List)

    @property
    def settings(self) -> Mapping[str, List[talon.Setting]]:
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
    def _typed_store(self, cls: type[GroupDataVar]) -> Dict[str, List[GroupDataVar]]:
        ...

    @overload
    def _typed_store(
        self, cls: type[talon.Callback]
    ) -> Dict[talon.EventCode, List[talon.Callback]]:
        ...

    @overload
    def _typed_store(self, cls: type[Data]) -> Dict[Any, Any]:
        ...

    def _typed_store(self, cls: type[Data]) -> Dict[Any, Any]:
        # If the data is not serialisable, store it in temp_data:
        if cls.serialisable:
            data = self._data
        else:
            data = self._temp_data
        # Store the data in a dictionary indexed by its type name.
        store = data.setdefault(cls.__name__, {})
        assert isinstance(store, dict)
        return store

    ##################################################
    # Encoder/Decoder
    ##################################################

    def to_dict(self) -> JsonValue:
        return {
            talon.Command.__name__: {
                name: [command.to_dict() for command in group]
                for name, group in self.commands.items()
            },
            talon.Action.__name__: {
                name: [action.to_dict() for action in group]
                for name, group in self.actions.items()
            },
            talon.Capture.__name__: {
                name: [capture.to_dict() for capture in group]
                for name, group in self.captures.items()
            },
            talon.List.__name__: {
                name: [list.to_dict() for list in group]
                for name, group in self.lists.items()
            },
            talon.Setting.__name__: {
                name: [setting.to_dict() for setting in group]
                for name, group in self.settings.items()
            },
            talon.Mode.__name__: {
                name: mode.to_dict() for name, mode in self.modes.items()
            },
            talon.Tag.__name__: {
                name: tag.to_dict() for name, tag in self.tags.items()
            },
        }

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
        if self is not None and self != Registry._active_global_registry:
            _LOGGER.warning(f"attempted to deactivate registry that is inactive")
        Registry._active_global_registry = None

    ##################################################
    # The active package, file, module, or context
    ##################################################

    def get_active_package(self) -> talon.Package:
        """
        Retrieve the active package.
        """
        try:
            if self._active_package is not None:
                return self._active_package
        except AttributeError:
            pass
        raise NoActivePackage()

    def get_active_file(self) -> talon.File:
        """
        Retrieve the active file.
        """
        try:
            if self._active_file is not None:
                return self._active_file
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
