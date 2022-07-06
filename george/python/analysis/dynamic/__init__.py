from abc import ABC
from george.types import PythonFileInfo
from pathlib import Path
from typing import Callable, Optional

import importlib
import os
import sys


class Register(ABC):
    def register(self, topic: str, cb: Callable) -> None:
        pass

    def unregister(self, topic: str, cb: Callable) -> None:
        pass


class Stub:
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

    def __getattr__(self, path: str) -> "Stub":
        return self

    def __call__(self, *args, **kwargs) -> "Stub":
        return self


class PythonDynamicPackageAnalysis:
    @staticmethod
    def process_package(package_root: Path):
        package_name = package_root.parts[-1]
        package_path = os.path.join(*package_root.parts[:-1])

        stubs_path = os.path.join(os.path.dirname(__file__), "stubs")

        class StubPathFinder(importlib.machinery.PathFinder):
            """
            Makes the stubs directory available under 'talon'.
            """

            @classmethod
            def find_spec(cls, fullname, path=None, target=None):
                if fullname == "talon" or fullname.startswith("talon."):
                    # Load talon stubs
                    return super().find_spec(fullname, [stubs_path])
                if fullname == "talon_plugins" or fullname.startswith("talon_plugins."):
                    # Load talon_plugins stubs
                    return super().find_spec(fullname, [stubs_path])
                elif fullname == package_name or fullname.startswith(
                    f"{package_name}."
                ):
                    # Load user submodules
                    return super().find_spec(fullname, [package_path])
                else:
                    # Allow normal sys.path stuff to handle everything else
                    return None

        # Add the StubPathFinder
        sys.meta_path.append(StubPathFinder)

        for file_path in package_root.glob("**/*.py"):
            file_path = file_path.relative_to(package_root)
            file_info = PythonDynamicFileAnalysis.process_file(file_path, package_root)


class PythonDynamicFileAnalysis:
    file_path: Path
    package_root: Path
    python_file_info: PythonFileInfo

    def __init__(self, file_path: Path, package_root: Path):
        self.file_path = file_path
        self.package_root = package_root
        self.python_file_info = PythonFileInfo(
            file_path=str(file_path),
            declarations={},
            overrides={},
            uses={},
        )

    def process(self):
        global current_python_dynamic_file_analysis
        current_python_dynamic_file_analysis = self
        package_name = self.package_root.parts[-1]
        module_path = ".".join((package_name, *self.file_path.with_suffix("").parts))
        importlib.import_module(module_path, package=self.package_root.parts[-1])

    @staticmethod
    def process_file(file_path: Path, package_root: Path) -> PythonFileInfo:
        analysis = PythonDynamicFileAnalysis(file_path, package_root)
        analysis.process()
        return analysis.python_file_info


current_python_dynamic_file_analysis: Optional[PythonDynamicFileAnalysis] = None
