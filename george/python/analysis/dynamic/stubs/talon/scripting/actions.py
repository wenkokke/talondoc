
from typing import Union
from george.python.analysis.dynamic import Stub


class ActionPath(Stub):
    pass


class ActionClassProxy(Stub):
    pass


class Actions:
    def __getattr__(self, path: str) -> ActionPath:
        return Stub()

    def sleep(self, duration: Union[float, str]):
        pass

    def list(self, prefix: str = None) -> None:
        pass

    def find(self, search: str, *, inactive: bool = None) -> None:
        pass

    @property
    def next(self) -> ActionPath:
        pass

    def __dir__(self):
        pass
