from abc import ABC
from types import ModuleType
from george.types import PythonFileInfo
from pathlib import Path
from typing import *

from importlib.abc import Loader
from importlib.machinery import ModuleSpec, PathFinder

import os
import sys


def _has_prefix(path: str, *prefixes: str):
    for prefix in prefixes:
        if path == prefix or path.startswith(prefix + "."):
            return True
    return False


class PythonDynamicPackageAnalysis:
    current_file_analysis: Optional["PythonDynamicFileAnalysis"] = None

    @classmethod
    def clear_file_analysis(cls):
        cls.current_file_analysis = None

    @classmethod
    def set_file_analysis(cls, file_analysis: "PythonDynamicFileAnalysis"):
        cls.current_file_analysis = file_analysis

    @classmethod
    def get_file_analysis(cls) -> "PythonDynamicFileAnalysis":
        return cls.current_file_analysis

    @classmethod
    def process_package(cls, pkg_root: Path):
        PKG_NAME = pkg_root.parts[-1]
        PKG_PATH = os.path.join(*pkg_root.parts[:-1])

        class PkgPathFinder(PathFinder):
            """
            Makes the package available.
            """

            @classmethod
            def find_spec(cls, fullname, path=None, target=None):
                if _has_prefix(fullname, PKG_NAME):
                    return super().find_spec(fullname, [PKG_PATH])
                else:
                    # Allow normal sys.path stuff to handle everything else
                    return None

        # Add the PkgPathFinder
        sys.meta_path.append(PkgPathFinder)

        for file_path in pkg_root.glob("**/*.py"):
            file_path = file_path.relative_to(pkg_root)
            file_analysis = PythonDynamicFileAnalysis(file_path, pkg_root)
            cls.set_file_analysis(file_analysis)
            file_analysis.process()
            cls.clear_file_analysis()

        sys.meta_path.remove(PkgPathFinder)


class PythonDynamicFileAnalysis:
    file_path: Path
    pkg_root: Path
    python_file_info: PythonFileInfo
    on_ready: list[Callable]

    def __init__(self, file_path: Path, pkg_root: Path):
        self.file_path = file_path
        self.pkg_root = pkg_root
        self.python_file_info = PythonFileInfo(
            file_path=str(file_path),
            declarations={},
            overrides={},
            uses={},
        )
        self.on_ready = []

    def register(self, topic: Union[int, str], cb: Callable) -> None:
        if topic == "ready":
            self.on_ready.append(cb)
        pass

    def unregister(self, topic: Union[int, str], cb: Callable) -> None:
        pass

    def process(self):
        pkg_name = self.pkg_root.parts[-1]
        module_path = ".".join((pkg_name, *self.file_path.with_suffix("").parts))
        __import__(module_path, globals(), locals(), [])
        for call_on_ready in self.on_ready:
            call_on_ready()
        self.on_ready.clear()


class Register(ABC):
    def register(self, topic: Union[int, str], cb: Callable) -> None:
        PythonDynamicPackageAnalysis.get_file_analysis().register(topic, cb)

    def unregister(self, topic: Union[int, str], cb: Callable) -> None:
        PythonDynamicPackageAnalysis.get_file_analysis().unregister(topic, cb)


class Stub(Register):
    def __init__(self, **kwargs):
        pass

    def __add__(self, other):
        return self

    def __sub__(self, other):
        return self

    def __mul__(self, other):
        return self

    def __pow__(self, other):
        return self

    def __mod__(self, other):
        return self

    def __floordiv__(self, other):
        return self

    def __truediv__(self, other):
        return self

    def __radd__(self, other):
        return self

    def __rsub__(self, other):
        return self

    def __rmul__(self, other):
        return self

    def __rmod__(self, other):
        return self

    def __rfloordiv__(self, other):
        return self

    def __rtruediv__(self, other):
        return self

    def __abs__(self):
        return self

    def __neg__(self):
        return self

    def __trunc__(self):
        return self

    def __floor__(self):
        return self

    def __ceil__(self):
        return self

    def __and__(self, other):
        return self

    def __rand__(self, other):
        return self

    def __or__(self, other):
        return self

    def __ror__(self, other):
        return self

    def __xor__(self, other):
        return self

    def __rxor__(self, other):
        return self

    def __invert__(self):
        return self

    def __lshift__(self, other):
        return self

    def __rlshift__(self, other):
        return self

    def __rshift__(self, other):
        return self

    def __rrshift__(self, other):
        return self

    def __getattr__(self, path: str) -> "Stub":
        return self

    def __call__(self, *args, **kwargs) -> "Stub":
        return self

    def __iter__(self) -> Iterator:
        return ().__iter__()


class StubFinder(PathFinder):
    """
    Makes the stubs available under 'talon' and 'talon_plugins'.
    """

    TALON_PKG_PATH = os.path.dirname(__file__)

    class StubModule(ModuleType, Stub):
        def __init__(fullname: str):
            super(ModuleType, fullname)

    class StubLoader(Loader):
        def create_module(cls, spec: ModuleSpec):
            return cls.load_module(spec.name)

        def exec_module(cls, module: ModuleType):
            pass

        def load_module(cls, fullname):
            return StubFinder.StubModule()

    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        if _has_prefix(fullname, "talon", "talon_plugins"):
            spec = super().find_spec(fullname, [cls.TALON_PKG_PATH])
            if spec:
                return spec
            else:
                return ModuleSpec(fullname, cls.StubLoader())
        return None


sys.meta_path.append(StubFinder)
