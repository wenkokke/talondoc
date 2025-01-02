from typing import TypeGuard

builtin_number_types: tuple[type, ...] = (
    int,
    float,
    complex,
)


def is_builtin_number_type(obj: object) -> TypeGuard[int | float | complex]:
    return isinstance(obj, builtin_number_types)


builtin_string_types: tuple[type, ...] = (str,)


def is_builtin_string_type(obj: object) -> TypeGuard[str]:
    return isinstance(obj, builtin_string_types)


builtin_types: tuple[type, ...] = (
    *builtin_number_types,
    list,
    tuple,
    range,
    *builtin_string_types,
    bytes,
    bytearray,
    memoryview,
    set,
    frozenset,
    dict,
)

builtin_type_names: tuple[str, ...] = tuple(ty.__name__ for ty in builtin_types)
