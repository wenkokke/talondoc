from enum import IntEnum
from george.python.analysis.dynamic import Stub


class ClickState(IntEnum):
    NONE: int
    DOWN: int
    CLICK: int
    CANCEL: int


class SizeConstraint(Stub):
    pass


class MaxConstraint(SizeConstraint):
    pass


class Size(Stub):
    pass


class State(Stub):
    pass


class Widget(Stub):
    pass


class Layout(Widget):
    pass


class VerticalLayout(Layout):
    pass


class HorizontalLayout(Layout):
    pass


class FixedLayout(Layout):
    pass


class Text(Widget):
    pass


class HSpacer(Widget):
    pass


class HLine(HSpacer):
    pass


class Canvas(Widget):
    pass


class Button(Widget):
    pass


class Slider(Widget):
    pass


class GUI(Stub):
    pass


def open(**kwargs):
    def __decorator(func):
        return func

    return __decorator
