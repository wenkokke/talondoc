from typing import Callable


KEY: int = 0
MCLICK: int = 0
MMOVE: int = 0
SCROLL: int = 0
ALL: int = 0
HOOK: int = 0
DOWN: int = 0
UP: int = 0
CTRL: int = 0
ALT: int = 0
SHIFT: int = 0
CMD: int = 0
SUPER = CMD
WIN = CMD
FN: int = 0
DRAG: int = 0
MODS: list[tuple[str, int]] = []


def register(topic: int, cb: Callable) -> None:
    pass


def unregister(topic: int, cb: Callable) -> None:
    pass
