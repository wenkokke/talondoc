from collections.abc import Callable
from inspect import Parameter, Signature, _ParameterKind
from typing import (
    TYPE_CHECKING,
    Any,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

from typing_extensions import TypeGuard, TypeVar

if TYPE_CHECKING:
    from . import Context, File, Module, Package
else:
    Package = type
    File = type
    Module = type
    Context = type


##############################################################################
# Encoding/Decoding
##############################################################################

_FieldType = TypeVar("_FieldType")


def field_any(
    fields: Mapping[str, Any],
    key: str,
    *,
    cls: Optional[type[_FieldType]] = None,
    guard: Optional[Callable[[Any], TypeGuard[_FieldType]]] = None,
    parse: Optional[Callable[[Any], _FieldType]] = None,
    default: Optional[_FieldType] = None,
) -> _FieldType:
    assert isinstance(fields, Mapping)
    try:
        value = fields[key]
        if parse is not None and callable(parse):
            value = parse(value)
        if guard is not None or cls is not None:
            if guard is not None and guard(value):
                return value
            try:
                if cls is not None and isinstance(value, cls):
                    return value
            except TypeError as e:
                pass
            raise TypeError(f"Expected {key} of type {cls}, found {type(value)}")
        else:
            return value  # type: ignore
    except KeyError as e:
        if default is not None:
            return default
        else:
            raise e


def field_int(fields: Mapping[str, Any], name: str) -> int:
    assert isinstance(fields, Mapping)
    return field_any(fields, name, cls=int)


def field_optint(fields: Mapping[str, Any], name: str) -> Optional[int]:
    assert isinstance(fields, Mapping)
    try:
        return field_int(fields, name)
    except KeyError:
        return None


def field_str(fields: Mapping[str, Any], name: str) -> str:
    assert isinstance(fields, Mapping)
    return field_any(fields, name, cls=str)


def field_optstr(fields: Mapping[str, Any], name: str) -> Optional[str]:
    assert isinstance(fields, Mapping)
    try:
        return field_str(fields, name)
    except KeyError:
        return None


_ParentType = TypeVar(
    "_ParentType",
    bound=Union[type[Package], type[File], type[Module], type[Context]],
)


def field_parent_type(
    fields: Mapping[str, Any],
    options: tuple[_ParentType, ...],
) -> _ParentType:
    assert isinstance(fields, Mapping)
    return {val.__name__: val for val in options}[field_str(fields, "parent_type")]


def parse_type(type_name: str) -> Optional[type]:
    return {
        "bool": bool,
        "dict": dict,
        "float": float,
        "int": int,
        "list": list,
        "set": set,
        "str": str,
        "tuple": tuple,
    }.get(type_name, None)


def parse_kind(kind: int) -> _ParameterKind:
    options: Tuple[int, ...] = (
        Parameter.POSITIONAL_ONLY,
        Parameter.POSITIONAL_OR_KEYWORD,
        Parameter.VAR_POSITIONAL,
        Parameter.KEYWORD_ONLY,
        Parameter.VAR_KEYWORD,
    )
    if kind in options:
        return cast(_ParameterKind, kind)
    raise TypeError(f"Expected kind in [{', '.join(map(str,options))}], found {kind}")


def parse_parameter(
    fields: Mapping[str, Any],
) -> Parameter:
    assert isinstance(fields, Mapping)
    return Parameter(
        name=field_str(fields, "name"),
        kind=parse_kind(field_int(fields, "kind")),
        default=field_any(fields, "default", default=Parameter.empty),
        annotation=field_any(fields, "annotation", parse=parse_type) or Parameter.empty,
    )


def field_parameters(fields: Mapping[str, Any]) -> Optional[Sequence[Parameter]]:
    assert isinstance(fields, Mapping)
    try:
        buffer: List[Parameter] = []
        for parameter_fields in field_any(fields, "parameters", cls=Sequence):
            if isinstance(parameter_fields, Mapping):
                buffer.append(parse_parameter(parameter_fields))
        return buffer
    except KeyError:
        return None


def field_return_annotation(fields: Mapping[str, Any]) -> type:
    assert isinstance(fields, Mapping)
    return field_any(fields, "return_annotation", parse=parse_type) or Signature.empty


def parse_signature(
    fields: Mapping[str, Any],
) -> Signature:
    assert isinstance(fields, Mapping)
    return Signature(
        parameters=field_parameters(fields),
        return_annotation=field_return_annotation(fields),
    )


def field_function_type_hints(
    fields: Mapping[str, Any],
) -> Optional[Signature]:
    assert isinstance(fields, Mapping)

    def _ismapping(value: Any) -> TypeGuard[Mapping]:
        return isinstance(value, Mapping)

    function_type_hint_fields: Mapping[str, Any]
    try:
        function_type_hint_fields = field_any(
            fields,
            "function_type_hints",
            guard=_ismapping,
        )
    except KeyError:
        return None

    return parse_signature(function_type_hint_fields)
