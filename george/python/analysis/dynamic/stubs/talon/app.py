from typing import Any, Callable
from sys import platform as platform_name


def register(topic: str, cb: Callable) -> None:
    pass


def unregister(topic: str, cb: Callable) -> None:
    pass


platform = {
    "linux": "linux",
    "darwin": "mac",
    "win32": "windows",
}[platform_name]
