from typing import Set, Tuple


def mouse_move(x: float, y: float, **kwargs):
    pass


def mouse_click(**kwargs) -> None:
    pass


def mouse_scroll(**kwargs) -> None:
    pass


def mouse_buttons_down() -> Set[int]:
    pass


def mouse_pos() -> Tuple[float, float]:
    pass


def cursor_visible(value: bool) -> None:
    pass


def key_press(key: str, **kwargs) -> None:
    pass
