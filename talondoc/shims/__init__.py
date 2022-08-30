import contextlib
import importlib.abc
import importlib.machinery
import sys
import types
import typing

from ..analyze.registry import Registry

from .core import ModuleShim
from .talon import TalonShim


class TalonShimFinder(importlib.abc.MetaPathFinder):
    """
    Makes the shims available under 'talon' and 'talon_plugins'.
    """

    PACKAGES: typing.ClassVar[tuple[str, ...]] = ("talon", "talon_plugins")

    class TalonShimLoader(importlib.abc.Loader):
        def create_module(cls, spec: importlib.machinery.ModuleSpec):
            return cls.load_module(spec.name)

        def exec_module(cls, module: types.ModuleType):
            pass

        def load_module(cls, fullname: str):
            if fullname == "talon":
                return TalonShim()
            else:
                return ModuleShim(fullname)

    @classmethod
    def _is_module(cls, fullname: str) -> bool:
        return any(
            fullname == package or fullname.startswith(f"{package}.")
            for package in cls.PACKAGES
        )

    @classmethod
    def find_spec(cls, fullname: str, path=None, target=None):
        if cls._is_module(fullname):
            return importlib.machinery.ModuleSpec(
                name=fullname,
                loader=cls.TalonShimLoader(),
                is_package=True,
            )
        else:
            # Allow normal sys.path stuff to handle everything else
            return None


@contextlib.contextmanager
def talon_shims(registry: Registry):
    registry.activate()
    sys.meta_path.append(TalonShimFinder)  # type: ignore
    try:
        yield None
    finally:
        sys.meta_path.remove(TalonShimFinder)  # type: ignore
        Registry.activate(None)
