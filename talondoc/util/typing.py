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
    if argument:
        normalized = argument.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
        raise ValueError(f"Not a boolean '{argument}'")
    else:
        return False
