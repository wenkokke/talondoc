import collections.abc
import contextlib
import importlib
import importlib.abc
import importlib.machinery
import sys
import types

from ..types import *
from .registry import Registry


@contextlib.contextmanager
def python_package(
    package_entry: PackageEntry,
) -> collections.abc.Iterator[None]:
    package_name: str = package_entry.name
    package_path: str = str(package_entry.path)

    class PackagePathFinder(importlib.machinery.PathFinder):
        """
        Makes the package available.
        """

        class ImplicitInitLoader(importlib.abc.Loader):
            def create_module(cls, spec: importlib.machinery.ModuleSpec):
                return cls.load_module(spec.name)

            def exec_module(cls, module: types.ModuleType):
                pass

            def load_module(cls, fullname: str):
                return types.ModuleType(fullname)

        @classmethod
        def _is_module(cls, fullname: str):
            return fullname == package_name or fullname.startswith(f"{package_name}.")

        @classmethod
        def _module_path(cls, fullname: str) -> pathlib.Path:
            assert cls._is_module(fullname)
            return pathlib.Path("/".join(fullname.split(".")[1:]))

        @classmethod
        def _is_dir(cls, fullname: str) -> bool:
            assert cls._is_module(fullname)
            return cls._module_path(fullname).is_dir()

        @classmethod
        def find_spec(cls, fullname: str, path=None, target=None):
            if cls._is_module(fullname):
                if cls._module_path(fullname).is_dir():
                    return importlib.machinery.ModuleSpec(
                        name=fullname,
                        loader=cls.ImplicitInitLoader(),
                        is_package=True,
                    )
                else:
                    return super().find_spec(fullname, [package_path])
            else:
                # Allow normal sys.path stuff to handle everything else
                return None

    sys.meta_path.append(PackagePathFinder)  # type: ignore
    try:
        yield None
    finally:
        sys.meta_path.remove(PackagePathFinder)  # type: ignore


def analyse_python_file(
    registry: Registry, python_file: pathlib.Path, package_entry: PackageEntry
) -> PythonFileEntry:

    # Register file:
    python_file_entry = PythonFileEntry(package=package_entry, path=python_file)
    registry.register(python_file_entry)

    # Process file:
    module_name = ".".join([package_entry.name, *python_file.with_suffix("").parts])
    importlib.import_module(name=module_name, package=package_entry.name)

    return python_file_entry
