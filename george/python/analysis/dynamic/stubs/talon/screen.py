from george.python.analysis.dynamic import Stub
from .types import Point2d as Point2d, Rect as Rect
from typing import Any, Callable, Dict, Optional, Sequence, Tuple


class ScreenFingerprint(Stub):
    pass


class Screen(Stub):
    pass


class ScreenMonitor(Stub):
    pass


def main_screen():
    return Screen()
