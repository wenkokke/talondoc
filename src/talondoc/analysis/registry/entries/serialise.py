from collections.abc import Callable
from inspect import Parameter, Signature
from typing import Any, Dict, Mapping, Optional, Sequence, Union

from typing_extensions import TypeVar

_T = TypeVar("_T")

##############################################################################
# Decoder
##############################################################################


def asdict_object(obj: object) -> Optional[str]:
    if obj in (Signature.empty, Parameter.empty):
        return None
    return repr(obj)


def asdict_class(cls: type) -> Optional[str]:
    if cls in (Signature.empty, Parameter.empty):
        return None
    if hasattr(cls, "__name__"):
        return cls.__name__
    return repr(cls)


def asdict_parameter(par: Parameter) -> Dict[str, Any]:
    return {
        "name": par.name,
        "kind": par.kind,
        "default": asdict_object(par.default),
        "annotation": asdict_class(par.annotation),
    }


def asdict_signature(sig: Signature) -> Dict[str, Any]:
    return {
        "parameters": [asdict_parameter(par) for par in sig.parameters.values()],
        "return_annotation": asdict_class(sig.return_annotation),
    }


##############################################################################
# Decoder
##############################################################################


def parse_value_by_type(cls: type[_T]) -> Callable[[Any], _T]:
    def _parser(value: Any) -> _T:
        if isinstance(value, cls):
            return value
        raise TypeError(f"Expected {cls.__name__}, found {type(value)}")

    return _parser


parse_int = parse_value_by_type(int)
parse_str = parse_value_by_type(str)
parse_list = parse_value_by_type(list)
parse_dict = parse_value_by_type(dict)


def parse_opt(parser: Callable[[Any], _T]) -> Callable[[Any], Optional[_T]]:
    def _parser(value: Any) -> Optional[_T]:
        if value is None:
            return None
        else:
            return parser(value)

    return _parser


parse_optint = parse_opt(parse_int)
parse_optstr = parse_opt(parse_str)
parse_optlist = parse_opt(parse_list)
parse_optdict = parse_opt(parse_dict)


def parse_field(name: str, parser: Callable[[Any], _T]) -> Callable[[Any], _T]:
    def _parser(value: Any) -> _T:
        value = parse_dict(value)
        try:
            return parser(value[name])
        except TypeError as e:
            raise TypeError(
                f"Error when checking type for field '{name}'. {e}"
            ).with_traceback(e.__traceback__)

    return _parser


def parse_optfield(
    name: str, parser: Callable[[Any], _T]
) -> Callable[[Any], Optional[_T]]:
    def _parser(value: Any) -> Optional[_T]:
        try:
            return parse_field(name, parse_opt(parser))(value)
        except KeyError as e:
            return None

    return _parser


def parse_value(options: tuple[_T, ...]) -> Callable[[Any], _T]:
    OPTIONS_DICT = {opt: opt for opt in options}
    return lambda value: OPTIONS_DICT[value]


def parse_class(*options: type[_T]) -> Callable[[Any], type[_T]]:
    return lambda value: {opt.__name__: opt for opt in options}[value]


parse_type = parse_class(bool, dict, float, int, list, set, str, tuple)
parse_kind = parse_value(
    (
        Parameter.POSITIONAL_ONLY,
        Parameter.POSITIONAL_OR_KEYWORD,
        Parameter.VAR_POSITIONAL,
        Parameter.KEYWORD_ONLY,
        Parameter.VAR_KEYWORD,
    )
)


def parse_parameter(value: Any) -> Parameter:
    return Parameter(
        name=parse_field("name", parse_str)(value),
        kind=parse_field("kind", parse_kind)(value),
        default=parse_optfield("default", parse_str)(value),
        annotation=parse_optfield("annotation", parse_type)(value),
    )


def parse_parameters(value: Any) -> Sequence[Parameter]:
    return tuple(map(parse_parameter, parse_list(value)))


def parse_signature(value: Any) -> Signature:
    return Signature(
        parameters=parse_field("parameters", parse_parameters)(value),
        return_annotation=parse_field("return_annotation", parse_type)(value),
    )
