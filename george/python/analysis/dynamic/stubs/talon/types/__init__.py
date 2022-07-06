from enum import IntEnum
from typing import *
from george.python.analysis.dynamic import Stub
from .point import Point2d as Point2d, Point3d as Point3d, Point6d as Point6d


class NameEnum(IntEnum):
    @classmethod
    def parse(cls, value: Union[int, str]):
        pass


class Rect(Stub):
    pass


class Size2d(Stub):
    pass


class Span(Stub):
    pass
