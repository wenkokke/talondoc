from abc import ABC
import importlib
from types import ModuleType
from george.types import PythonFileInfo, PythonPackageInfo
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
    current_package_analysis: Optional["PythonDynamicPackageAnalysis"] = None
    current_file_analysis: Optional["PythonDynamicFileAnalysis"] = None

    def __init__(self, package_root: Path):
        self.package_root = package_root
        self.package_name = package_root.parts[-1]
        self.package_path = os.path.join(*package_root.parts[:-1])
        self.python_package_info = PythonPackageInfo(package_root=str(package_root))

    @classmethod
    def clear_file_analysis(cls):
        cls.current_file_analysis = None

    @classmethod
    def set_file_analysis(cls, file_analysis: "PythonDynamicFileAnalysis"):
        cls.current_file_analysis = file_analysis

    @classmethod
    def get_file_info(cls) -> PythonFileInfo:
        return cls.get_file_analysis().python_file_info

    @classmethod
    def get_file_analysis(cls) -> "PythonDynamicFileAnalysis":
        return cls.current_file_analysis

    @classmethod
    def clear_package_analysis(cls):
        cls.current_package_analysis = None

    @classmethod
    def set_package_analysis(cls, package_analysis: "PythonDynamicPackageAnalysis"):
        cls.current_package_analysis = package_analysis

    @classmethod
    def get_package_analysis(cls) -> "PythonDynamicPackageAnalysis":
        return cls.current_package_analysis

    @classmethod
    def get_package_info(cls) -> PythonPackageInfo:
        return cls.get_package_analysis().python_package_info

    def process(self) -> PythonPackageInfo:
        PythonDynamicPackageAnalysis.set_package_analysis(self)

        class PkgPathFinder(PathFinder):
            """
            Makes the package available.
            """

            @classmethod
            def find_spec(cls, fullname, path=None, target=None):
                if _has_prefix(fullname, self.package_name):
                    return super().find_spec(fullname, [self.package_path])
                else:
                    # Allow normal sys.path stuff to handle everything else
                    return None

        sys.meta_path.append(PkgPathFinder)

        file_analyses = []
        for file_path in self.package_root.glob("**/*.py"):
            file_path = file_path.relative_to(self.package_root)
            file_analysis = PythonDynamicFileAnalysis(file_path, self.package_root)
            self.python_package_info.file_infos[
                str(file_path)
            ] = file_analysis.python_file_info
            PythonDynamicPackageAnalysis.set_file_analysis(file_analysis)
            file_analysis.process()
            PythonDynamicPackageAnalysis.clear_file_analysis()
            file_analyses.append(file_analysis)

        for file_analysis in file_analyses:
            PythonDynamicPackageAnalysis.set_file_analysis(file_analysis)
            file_analysis.ready()
            PythonDynamicPackageAnalysis.clear_file_analysis()

        sys.meta_path.remove(PkgPathFinder)

        PythonDynamicPackageAnalysis.clear_package_analysis()

        return self.python_package_info


class PythonDynamicFileAnalysis:
    def __init__(self, file_path: Path, package_root: Path):
        self.file_path = file_path
        self.package_root = package_root
        self.python_file_info = PythonFileInfo(
            file_path=str(file_path), package_root=str(package_root)
        )
        self.on_ready = []

    def register(self, topic: Union[int, str], cb: Callable) -> None:
        if topic == "ready":
            self.on_ready.append(cb)

    def unregister(self, topic: Union[int, str], cb: Callable) -> None:
        if topic == "ready":
            self.on_ready.remove(cb)

    def ready(self):
        for cb in self.on_ready:
            cb()

    def process(self):
        package_name = self.package_root.parts[-1]
        module_path = ".".join((package_name, *self.file_path.with_suffix("").parts))
        importlib.import_module(module_path)


class Register(ABC):
    def register(self, topic: Union[int, str], cb: Callable) -> None:
        PythonDynamicPackageAnalysis.get_file_analysis().register(topic, cb)

    def unregister(self, topic: Union[int, str], cb: Callable) -> None:
        PythonDynamicPackageAnalysis.get_file_analysis().unregister(topic, cb)


class Stub(Register):
    def __init__(self, **kwargs):
        pass

    @property
    def _package_info(self) -> PythonPackageInfo:
        return PythonDynamicPackageAnalysis.get_package_info()

    @property
    def _file_info(self) -> PythonFileInfo:
        return PythonDynamicPackageAnalysis.get_file_info()

    def __getattr__(self, path: str) -> "Stub":
        try:
            return object.__getattribute__(self, path)
        except AttributeError:
            return self

    def __setattr__(self, path: str, value: Any):
        pass

    def __getitem__(self, path: str) -> "Stub":
        return self

    def __setitem__(self, path: str, value: Any):
        pass

    def __add__(self, other) -> "Stub":
        return self

    def __sub__(self, other) -> "Stub":
        return self

    def __mul__(self, other) -> "Stub":
        return self

    def __pow__(self, other) -> "Stub":
        return self

    def __mod__(self, other) -> "Stub":
        return self

    def __floordiv__(self, other) -> "Stub":
        return self

    def __truediv__(self, other) -> "Stub":
        return self

    def __radd__(self, other) -> "Stub":
        return self

    def __rsub__(self, other) -> "Stub":
        return self

    def __rmul__(self, other) -> "Stub":
        return self

    def __rmod__(self, other) -> "Stub":
        return self

    def __rfloordiv__(self, other) -> "Stub":
        return self

    def __rtruediv__(self, other) -> "Stub":
        return self

    def __abs__(self) -> "Stub":
        return self

    def __neg__(self) -> "Stub":
        return self

    def __trunc__(self) -> "Stub":
        return self

    def __floor__(self) -> "Stub":
        return self

    def __ceil__(self) -> "Stub":
        return self

    def __and__(self, other) -> "Stub":
        return self

    def __rand__(self, other) -> "Stub":
        return self

    def __or__(self, other) -> "Stub":
        return self

    def __ror__(self, other) -> "Stub":
        return self

    def __xor__(self, other) -> "Stub":
        return self

    def __rxor__(self, other) -> "Stub":
        return self

    def __invert__(self) -> "Stub":
        return self

    def __lshift__(self, other) -> "Stub":
        return self

    def __rlshift__(self, other) -> "Stub":
        return self

    def __rshift__(self, other) -> "Stub":
        return self

    def __rrshift__(self, other) -> "Stub":
        return self

    def __call__(self, *args, **kwargs) -> "Stub":
        return self

    def __iter__(self) -> Iterator:
        return ().__iter__()


class StubFinder(PathFinder):
    """
    Makes the stubs available under 'talon' and 'talon_plugins'.
    """

    TALON_PACKAGE_PATH = os.path.dirname(__file__)

    class StubModule(ModuleType, Stub):
        def __init__(self, fullname: str):
            ModuleType.__init__(self, fullname)

    class StubLoader(Loader):
        def create_module(cls, spec: ModuleSpec):
            return cls.load_module(spec.name)

        def exec_module(cls, module: ModuleType):
            pass

        def load_module(cls, fullname):
            return StubFinder.StubModule(fullname)

    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        if _has_prefix(fullname, "talon", "talon_plugins"):
            spec = super().find_spec(fullname, [cls.TALON_PACKAGE_PATH])
            if spec:
                return spec
            else:
                return ModuleSpec(fullname, cls.StubLoader())
        return None


sys.meta_path.append(StubFinder)
