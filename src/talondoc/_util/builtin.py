builtin_number_types: tuple[type, ...] = (
    int,
    float,
    complex,
)

builtin_string_types: tuple[type, ...] = (str,)

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
