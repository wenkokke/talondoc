from typing import Callable, Generator
from george.python.analysis.dynamic import (
    Stub,
    register as register,
    unregister as unregister,
)
from .screen import Screen as Screen, Rect as Rect, main_screen as main_screen


class App(Stub):
    pass


class Window(Stub):
    pass

def apps(**kwargs) -> Generator[App, None, None]:
    yield App()