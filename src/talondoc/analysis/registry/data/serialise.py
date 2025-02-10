import base64
import pickle
from collections.abc import Callable, Mapping, Sequence
from functools import partial
from inspect import Parameter, Signature
from logging import WARNING
from typing import Any, TypeAlias

from typing_extensions import TypeVar

from ...._util.logging import getLogger

_LOGGER = getLogger(__name__)

_S = TypeVar("_S")
_T = TypeVar("_T")

JsonValue: TypeAlias = None | int | str | dict[str, "JsonValue"] | list["JsonValue"]

##############################################################################
# Decoder
##############################################################################


def asdict_opt(asdict: Callable[[_S], _T]) -> Callable[[_S | None], _T | None]:
    def _asdict(value: _S | None) -> _T | None:
        if value is None:
            return None
        return asdict(value)

    return _asdict


def asdict_pickle(value: Any) -> JsonValue:
    if isinstance(value, str):
        return value
    value = base64.b64encode(pickle.dumps(value)).decode(encoding="utf-8")
    return {"pickle": value}


def asdict_class(cls: type) -> JsonValue:
    if cls in (Signature.empty, Parameter.empty):
        return None
    if hasattr(cls, "__name__"):
        return cls.__name__
    return repr(cls)


def asdict_parameter(par: Parameter) -> JsonValue:
    return {
        "name": par.name,
        "kind": par.kind,
        "default": asdict_pickle(par.default),
        "annotation": asdict_class(par.annotation),
    }


def asdict_signature(sig: Signature) -> JsonValue:
    return {
        "parameters": [asdict_parameter(par) for par in sig.parameters.values()],
        "return_annotation": asdict_class(sig.return_annotation),
    }


##############################################################################
# Decoder
##############################################################################


def parse_pickle(value: JsonValue, *, context: dict[str, str] | None = None) -> Any:
    if context is None:
        context = {}
    if isinstance(value, str):
        return parse_str(value)
    if isinstance(value, Mapping):
        value = parse_str(value["pickle"])
        try:
            return pickle.loads(base64.b64decode(value, validate=True))
        except ModuleNotFoundError as e:
            if _LOGGER.isEnabledFor(WARNING):
                object_name = context.get("object_name")
                object_type = context.get("object_type", "object")
                field_name = context.get("field_name")
                field_path = context.get("field_path")
                message_buffer: list[str] = []
                message_buffer.append("Cannot decode")
                if field_name:
                    message_buffer.append(f"field {field_name}")
                else:
                    message_buffer.append("unknown field")
                if field_path:
                    message_buffer.append(f"in {field_path}")
                if object_name:
                    message_buffer.append(f"of {object_type} {object_name}.")
                else:
                    message_buffer.append(f"unknown {object_type}.")
                message_buffer.append(str(e))
                _LOGGER.warning(" ".join(message_buffer))
            return None
    else:
        raise TypeError(f"Expected str or dict, found {type(value).__name__}")


def parse_value_by_type(cls: type[_T]) -> Callable[[JsonValue], _T]:
    def _parser(value: Any) -> _T:
        if isinstance(value, cls):
            return value
        raise TypeError(f"Expected {cls.__name__}, found {type(value).__name__}")

    return _parser


parse_int = parse_value_by_type(int)
parse_str = parse_value_by_type(str)
parse_list = parse_value_by_type(list)
parse_dict = parse_value_by_type(dict)


def parse_list_of(parser: Callable[[JsonValue], _T]) -> Callable[[JsonValue], list[_T]]:
    return lambda value: list(map(parser, parse_list(value)))


def parse_opt(parser: Callable[[JsonValue], _T]) -> Callable[[JsonValue], _T | None]:
    def _parser(value: JsonValue) -> _T | None:
        if value is None:
            return None
        return parser(value)

    return _parser


parse_optint = parse_opt(parse_int)
parse_optstr = parse_opt(parse_str)
parse_optlist = parse_opt(parse_list)
parse_optdict = parse_opt(parse_dict)


def parse_field(
    name: str, parser: Callable[[JsonValue], _T]
) -> Callable[[JsonValue], _T]:
    def _parser(value: JsonValue) -> _T:
        value = parse_dict(value)
        try:
            return parser(value[name])
        except TypeError as e:
            raise TypeError(f"Error when checking type for field {name}. {e}") from e

    return _parser


def parse_optfield(
    name: str, parser: Callable[[JsonValue], _T]
) -> Callable[[JsonValue], _T | None]:
    def _parser(value: JsonValue) -> _T | None:
        try:
            return parse_field(name, parse_opt(parser))(value)
        except KeyError:
            return None

    return _parser


_EnumType = TypeVar("_EnumType", bound=int)


def parse_enum(options: Sequence[_EnumType]) -> Callable[[JsonValue], _EnumType]:
    OPTIONS_DICT = {int(opt): opt for opt in options}
    return lambda value: OPTIONS_DICT[parse_int(value)]


def parse_class(*options: type[_T]) -> Callable[[JsonValue], type[_T]]:
    return lambda value: {opt.__name__: opt for opt in options}[parse_str(value)]


parse_type = parse_class(bool, dict, float, int, list, set, str, tuple)
parse_kind = parse_enum(
    (
        Parameter.POSITIONAL_ONLY,
        Parameter.POSITIONAL_OR_KEYWORD,
        Parameter.VAR_POSITIONAL,
        Parameter.KEYWORD_ONLY,
        Parameter.VAR_KEYWORD,
    )
)


def parse_parameter(
    value: JsonValue, *, context: dict[str, str] | None = None
) -> Parameter:
    if context is None:
        context = {}
    return Parameter(
        name=parse_field("name", parse_str)(value),
        kind=parse_field("kind", parse_kind)(value),
        default=parse_optfield("default", partial(parse_pickle, context=context))(
            value
        ),
        annotation=parse_optfield("annotation", parse_type)(value),
    )


def parse_parameters(
    value: JsonValue, *, context: dict[str, str] | None = None
) -> Sequence[Parameter]:
    if context is None:
        context = {}
    return tuple(map(partial(parse_parameter, context=context), parse_list(value)))


def parse_signature(
    value: JsonValue, *, context: dict[str, str] | None = None
) -> Signature:
    if context is None:
        context = {}
    return Signature(
        parameters=parse_field(
            "parameters", partial(parse_parameters, context=context)
        )(value),
        return_annotation=parse_optfield("return_annotation", parse_type)(value),
    )
