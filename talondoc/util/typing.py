from typing import Optional


def optional_strlist(argument: Optional[str]) -> tuple[str, ...]:
    if argument:
        return tuple(pattern.strip() for pattern in argument.split(","))
    else:
        return ()


def optional_str(argument: Optional[str]) -> Optional[str]:
    if argument:
        return argument.strip()
    else:
        return None


def flag(argument: Optional[str]) -> bool:
    return True
