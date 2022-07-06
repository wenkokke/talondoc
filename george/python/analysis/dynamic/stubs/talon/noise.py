from typing import Callable
from george.python.analysis.dynamic import Stub


class NoiseStream(Stub):
    pass


class DeviceInfo(Stub):
    pass


class Noise(Stub):
    pass


def register(topic: str, cb: Callable) -> None:
    pass


def unregister(topic: str, cb: Callable) -> None:
    pass
