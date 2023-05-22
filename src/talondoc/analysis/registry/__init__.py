import inspect
import itertools
import json
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, fields
from functools import singledispatchmethod
from typing import Any, ClassVar, Optional, Union, cast, overload

import importlib_resources
from more_itertools import partition
from talonfmt import talonfmt
from typing_extensions import Final

from ..._util.logging import getLogger
from . import data
from .data import CallbackVar
from .data.abc import (
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
from .data.serialise import JsonValue, parse_dict, parse_list

_LOGGER = getLogger(__name__)


@dataclass
class Registry:
    _data: Final[dict[str, Any]]
    _temp_data: Final[dict[str, Any]]

    _active_package: Optional[data.Package] = None
    _active_file: Optional[data.File] = None

    def __init__(
        self,
        *,
        data: dict[str, Any] = {},
        temp_data: dict[str, Any] = {},
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
        _LOGGER.debug(f"Found declaration for {value.__class__.__name__} {value.name}")
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
        if isinstance(value, data.Package):
            self._active_package = value
        if isinstance(value, data.File):
            self._active_file = value
        return value

    def _register_grouped_data(self, value: GroupDataVar) -> GroupDataVar:
        # Print the value name to the log.
        _LOGGER.debug(
            " ".join(
                [
                    f"Found",
                    "declaration"
                    if issubclass(value.parent_type, data.Module)
                    else "override",
                    "for {value.__class__.__name__} {value.name}",
                ]
            )
        )
        # Register the data in the store.
        store = self._typed_store(value.__class__)
        store.setdefault(value.name, []).append(value)
        return value

    def _register_callback(self, value: CallbackVar) -> CallbackVar:
        # Print the value name to the log.
        _LOGGER.debug(f"Found declaration for {value.__class__.__name__} {value.name}")
        # Register the data in the store.
        self._typed_store(data.Callback).setdefault(value.event_code, []).append(value)
        return value

    # Simple entries
    register.register(data.Package, _register_simple_data)
    register.register(data.File, _register_simple_data)
    register.register(data.Function, _register_simple_data)
    register.register(data.Module, _register_simple_data)
    register.register(data.Context, _register_simple_data)
    register.register(data.Mode, _register_simple_data)
    register.register(data.Tag, _register_simple_data)

    # Group entries
    register.register(data.Command, _register_grouped_data)
    register.register(data.Action, _register_grouped_data)
    register.register(data.Capture, _register_grouped_data)
    register.register(data.List, _register_grouped_data)
    register.register(data.Setting, _register_grouped_data)

    # Callback entries
    register.register(data.Callback, _register_callback)

    def extend(self, values: Sequence[DataVar]) -> None:
        for value in values:
            self.register(value)

    ######################################################################
    # Finding Data
    ######################################################################

    def resolve_packages(
        self, packages: Iterator[Union[data.PackageName, data.Package]]
    ) -> Iterator[data.Package]:
        for package in packages:
            if isinstance(package, data.Package):
                yield package
            else:
                try:
                    yield self.get(data.Package, package)
                except UnknownReference as e:
                    _LOGGER.error(e)
                    pass

    def resolve_files(
        self, files: Iterator[Union[data.FileName, data.File]]
    ) -> Iterator[data.File]:
        for file in files:
            if isinstance(file, data.File):
                yield file
            else:
                try:
                    yield self.get(data.File, file)
                except UnknownReference as e:
                    _LOGGER.error(e)
                    pass

    def resolve_contexts(
        self, contexts: Iterator[Union[data.FileName, data.File, data.Context]]
    ) -> Iterator[data.Context]:
        for value in contexts:
            if isinstance(value, data.Context):
                yield value
            else:
                if isinstance(value, str):
                    try:
                        value = self.get(data.File, value)
                    except UnknownReference as e:
                        _LOGGER.error(e)
                        continue
                assert isinstance(value, data.File)
                for context_name in value.contexts:
                    yield self.get(data.Context, context_name, referenced_by=value)

    def get_commands(
        self,
        *,
        restrict_to: Optional[
            Iterator[Union[data.FileName, data.File, data.Context]]
        ] = None,
    ) -> Iterator[data.Command]:
        if restrict_to is None:
            for group in self.commands.values():
                assert isinstance(group, list), f"Unexpected value {group}"
                for command in group:
                    yield command
        else:
            for context in self.resolve_contexts(restrict_to):
                for command_name in context.commands:
                    yield self.get(data.Command, command_name, referenced_by=context)

    def find_commands(
        self,
        text: Sequence[str],
        *,
        fullmatch: bool = False,
        restrict_to: Optional[Iterator[Union[data.FileName, data.Context]]] = None,
    ) -> Iterator[data.Command]:
        for command in self.get_commands(restrict_to=restrict_to):
            if self.match(text, command.rule, fullmatch=fullmatch):
                yield command

    def match(
        self,
        text: Sequence[str],
        rule: data.Rule,
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
    _BUILTIN_CAPTURE_NAMES: ClassVar[Sequence[data.CaptureName]] = (
        "digit_string",
        "digits",
        "number",
        "number_signed",
        "number_small",
        "phrase",
        "word",
    )

    def _get_capture_rule(self, name: data.CaptureName) -> Optional[data.Rule]:
        """Get the rule for a capture. Hook for 'match'."""
        try:
            return self.get(data.Capture, name).rule
        except UnknownReference as e:
            # If the capture is not a builtin capture, log a warning:
            if name not in self.__class__._BUILTIN_CAPTURE_NAMES:
                _LOGGER.warning(e)
            return None

    def _get_list_value(self, name: data.ListName) -> Optional[data.ListValue]:
        """Get the values for a list. Hook for 'match'."""
        try:
            return self.get(data.List, name).value
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
            if value is None and issubclass(cls, data.File):
                value = cast(
                    Optional[DataVar],
                    # Try the search again with ".talon" suffixed:
                    self.lookup(cls, f"{name}.talon") or
                    # Try the search again with ".py" suffixed:
                    self.lookup(cls, f"{name}.py") or
                    # Try the search again assuming name is a path:
                    self.lookup(cls, f"user.{name.replace('/', '.')}"),
                )

        elif issubclass(cls, GroupData):
            declaration, defaults, others = self.lookup_partition(cls, name)
            for obj in itertools.chain((declaration,), defaults, others):
                if obj:
                    value = cast(DataVar, obj)
                    break
        elif issubclass(cls, data.Callback):
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
    ) -> Optional[list[GroupDataVar]]:
        ...

    @overload
    def lookup(
        self,
        cls: type[data.Callback],
        name: data.EventCode,
    ) -> Optional[Sequence[data.Callback]]:
        ...

    def lookup(self, cls: type[Data], name: Any) -> Optional[Any]:
        return self._typed_store(cls).get(self.resolve_name(name), None)

    def lookup_default(
        self, cls: type[GroupDataVar], name: str
    ) -> Optional[GroupDataVar]:
        declaration, default_overrides, other_overrides = self.lookup_partition(
            cls, name
        )
        return self._combine(cls, itertools.chain((declaration,), default_overrides))

    def _combine(
        self, cls: type[GroupDataVar], data: Iterator[Optional[GroupDataVar]]
    ) -> Optional[GroupDataVar]:
        init_keys: set[str] = {field.name for field in fields(cls) if field.init}
        init_args: dict[str, Any] = {}
        for datum in data:
            if isinstance(datum, cls):
                for name in init_keys:
                    init_args[name] = init_args.get(name, None) or getattr(datum, name)
        if init_args:
            return cls(**init_args)
        else:
            return None

    def lookup_description(self, cls: type[Data], name: Any) -> Optional[str]:
        if issubclass(cls, SimpleData):
            simple = self.lookup(cls, name)
            if simple:
                return simple.description
        if issubclass(cls, GroupData):
            default = self.lookup_default(cls, name)
            if default:
                return default.description
        return None

    def lookup_partition(
        self,
        cls: type[GroupDataVar],
        name: str,
    ) -> tuple[Optional[GroupDataVar], Sequence[GroupDataVar], Sequence[GroupDataVar]]:
        group = self.lookup(cls, name)
        if group:
            _IS_DECLARATION: int = 0
            _IS_ALWAYS_ON: int = 1

            def _complexity(obj: GroupDataVar) -> int:
                if issubclass(obj.parent_type, data.Module):
                    return _IS_DECLARATION
                else:
                    ctx = self.lookup(data.Context, obj.parent_name)
                    if ctx is None:
                        return _IS_ALWAYS_ON
                    else:
                        return _IS_ALWAYS_ON + len(ctx.matches)

            # Sort all objects in the group by the complexity of their matches:
            sorted_group = [(_complexity(obj), obj) for obj in group]
            sorted_group.sort(key=lambda tup: tup[0])

            # Extract all declarations:
            declarations_iter, overrides_iter = partition(
                lambda tup: tup[0] != _IS_DECLARATION, sorted_group
            )
            declarations = tuple(declarations_iter)
            if len(declarations) >= 2:
                _LOGGER.warning(DuplicateData([tup[1] for tup in declarations]))
            declaration = declarations[0][1] if len(declarations) >= 1 else None

            # Extract all overrides that are always on:
            default_overrides_iter, other_overrides_iter = partition(
                lambda tup: tup[0] != _IS_ALWAYS_ON, overrides_iter
            )

            default_overrides = tuple((tup[1] for tup in default_overrides_iter))
            other_overrides = tuple((tup[1] for tup in other_overrides_iter))
            if len(default_overrides) >= 2:
                # NOTE: We warn the user if there are multiple overrides which
                #       are always on, but suppress this warning for commands.
                if not issubclass(cls, data.Command):
                    _LOGGER.warning(DuplicateData(default_overrides))
            return (declaration, default_overrides, other_overrides)
        return (None, (), ())

    def lookup_default_function(
        self, cls: type[GroupDataHasFunction], name: str
    ) -> Optional[Callable[..., Any]]:
        # Find the default object:
        default = self.lookup_default(cls, name)

        # Find the associated function:
        if default is not None and default.function_name is not None:
            function = self.lookup(data.Function, default.function_name)
            if function is not None:
                # Create copy for _function_wrapper
                func = function.function

                def _function_wrapper(*args: Any, **kwargs: Any) -> Any:
                    func_name = func.__name__
                    func_type = inspect.signature(func)
                    act_argc = len(args) + len(kwargs)
                    exp_argc = len(func_type.parameters)
                    if act_argc != exp_argc:
                        act_argv: list[str] = []
                        act_argv.extend(map(str, args))
                        act_argv.extend(f"{key}={val}" for key, val in kwargs.items())
                        _LOGGER.warning(
                            f"mismatch in number of parameters for {func_name}\n"
                            f"expected: {func_type}\n"
                            f"found: ({', '.join(act_argv)})"
                        )
                    return func(*args, **kwargs)

                return _function_wrapper
        return None

    def resolve_name(self, name: str, *, package: Optional[data.Package] = None) -> str:
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
    # typed Access To Data
    ######################################################################

    @property
    def packages(self) -> Mapping[str, data.Package]:
        return self._typed_store(data.Package)

    @property
    def files(self) -> Mapping[str, data.File]:
        return self._typed_store(data.File)

    @property
    def functions(self) -> Mapping[str, data.Function]:
        return self._typed_store(data.Function)

    @property
    def callbacks(self) -> Mapping[data.EventCode, list[data.Callback]]:
        return self._typed_store(data.Callback)

    @property
    def modules(self) -> Mapping[str, data.Module]:
        return self._typed_store(data.Module)

    @property
    def contexts(self) -> Mapping[str, data.Context]:
        return self._typed_store(data.Context)

    @property
    def commands(self) -> Mapping[str, list[data.Command]]:
        return self._typed_store(data.Command)

    @property
    def actions(self) -> Mapping[str, list[data.Action]]:
        return self._typed_store(data.Action)

    @property
    def captures(self) -> Mapping[str, list[data.Capture]]:
        return self._typed_store(data.Capture)

    @property
    def lists(self) -> Mapping[str, list[data.List]]:
        return self._typed_store(data.List)

    @property
    def settings(self) -> Mapping[str, list[data.Setting]]:
        return self._typed_store(data.Setting)

    @property
    def modes(self) -> Mapping[str, data.Mode]:
        return self._typed_store(data.Mode)

    @property
    def tags(self) -> Mapping[str, data.Tag]:
        return self._typed_store(data.Tag)

    ######################################################################
    # Internal typed Access To Data
    ######################################################################

    @overload
    def _typed_store(self, cls: type[SimpleDataVar]) -> dict[str, SimpleDataVar]:
        ...

    @overload
    def _typed_store(self, cls: type[GroupDataVar]) -> dict[str, list[GroupDataVar]]:
        ...

    @overload
    def _typed_store(
        self, cls: type[data.Callback]
    ) -> dict[data.EventCode, list[data.Callback]]:
        ...

    @overload
    def _typed_store(self, cls: type[Data]) -> dict[Any, Any]:
        ...

    def _typed_store(self, cls: type[Data]) -> dict[Any, Any]:
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

    def load_builtin(self) -> None:
        self._load_from_dict(
            json.loads(
                importlib_resources.open_text(
                    "talondoc._cache_builtin.resources", "talon.json"
                ).read()
            )
        )

    def _load_from_dict(self, registry: JsonValue) -> None:
        registry = parse_dict(registry)
        for cls in (
            data.Command,
            data.Action,
            data.Capture,
            data.List,
            data.Setting,
            data.Mode,
            data.Tag,
        ):
            _LOGGER.debug(f"Loading builtin {cls.__name__} objects...")
            store = parse_dict(registry.get(cls.__name__, {}))
            if issubclass(cls, GroupData):
                for name, group in store.items():
                    for value in parse_list(group):
                        parsed_group_value = cls.from_dict(value)
                        if name != parsed_group_value.name:
                            _LOGGER.warning(
                                f"Found {cls.__name__} {parsed_group_value.name} in group for {name}"
                            )
                        self.register(parsed_group_value)

            elif issubclass(cls, (data.Mode, data.Tag)):
                for name, value in store.items():
                    parsed_simple_value = cls.from_dict(value)
                    if name != parsed_simple_value.name:
                        _LOGGER.warning(
                            f"Found {cls.__name__} {parsed_simple_value.name} in group for {name}"
                        )
                    self.register(parsed_simple_value)
            else:
                raise TypeError(f"Unexpected data class {cls.__name__}")

    def to_dict(self) -> JsonValue:
        return {
            data.Command.__name__: {
                name: [command.to_dict() for command in group]
                for name, group in self.commands.items()
            },
            data.Action.__name__: {
                name: [action.to_dict() for action in group]
                for name, group in self.actions.items()
            },
            data.Capture.__name__: {
                name: [capture.to_dict() for capture in group]
                for name, group in self.captures.items()
            },
            data.List.__name__: {
                name: [list.to_dict() for list in group]
                for name, group in self.lists.items()
            },
            data.Setting.__name__: {
                name: [setting.to_dict() for setting in group]
                for name, group in self.settings.items()
            },
            data.Mode.__name__: {
                name: mode.to_dict() for name, mode in self.modes.items()
            },
            data.Tag.__name__: {name: tag.to_dict() for name, tag in self.tags.items()},
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

    def activate(self: "Registry") -> None:
        """
        Activate this registry.
        """
        Registry._active_global_registry = self

    def deactivate(self: "Registry") -> None:
        """
        Deactivate this registry.
        """
        if self is not None and self != Registry._active_global_registry:
            _LOGGER.warning(f"attempted to deactivate registry that is inactive")
        Registry._active_global_registry = None

    ##################################################
    # The active package, file, module, or context
    ##################################################

    def get_active_package(self) -> data.Package:
        """
        Retrieve the active package.
        """
        try:
            if self._active_package is not None:
                return self._active_package
        except AttributeError:
            pass
        raise NoActivePackage()

    def get_active_file(self) -> data.File:
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
