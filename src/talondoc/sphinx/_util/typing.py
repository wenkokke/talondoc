from collections.abc import Sequence
from typing import Any


def optional_strlist(argument: str | None) -> Sequence[str]:
    if argument:
        return tuple(pattern.strip() for pattern in argument.split(","))
    return ()


def optional_str(argument: str | None) -> str | None:
    if argument:
        return argument.strip()
    return None


def optional_int(argument: str | None) -> int | None:
    if argument:
        return int(argument)
    return None


def flag(argument: Any) -> bool:
    return True
