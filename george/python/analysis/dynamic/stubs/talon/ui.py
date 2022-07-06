from typing import Callable
from george.python.analysis.dynamic import Stub
from .screen import Screen as Screen, Rect as Rect, main_screen as main_screen


class App(Stub):
    pass


class Window(Stub):
    pass


@staticmethod
def register(topic: str, cb: Callable) -> None:
    pass


@staticmethod
def unregister(topic: str, cb: Callable) -> None:
    pass
