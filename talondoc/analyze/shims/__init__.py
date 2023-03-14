import sys
from collections.abc import Iterator
from contextlib import contextmanager
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec, PathFinder
from pathlib import Path
from types import ModuleType
from typing import ClassVar, Optional, Union

from ...util.logging import getLogger
from ..entries.user import PackageEntry
from ..registry import Registry
from .core import ModuleShim, TalonShim

_LOGGER = getLogger(__name__)


class TalonShimFinder(MetaPathFinder):
    """
    Makes the shims available under 'talon' and 'talon_plugins'.
    """

    PACKAGES: ClassVar[tuple[str, ...]] = ("talon", "talon_plugins")

    class TalonShimLoader(Loader):
        def create_module(cls, spec: ModuleSpec):
            return cls.load_module(spec.name)

        def exec_module(cls, module: ModuleType):
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
            return ModuleSpec(
                name=fullname,
                loader=cls.TalonShimLoader(),
                is_package=True,
            )
        else:
            # Allow normal sys.path stuff to handle everything else
            return None


TalonPackage = Union[tuple[str, Union[str, Path]], PackageEntry]


@contextmanager
def talon_package(package: TalonPackage) -> Iterator[None]:
    if isinstance(package, PackageEntry):
        package_name = package.name
        package_path = str(package.path)
    else:
        package_name = package[0]
        package_path = str(package[1])

    class PackagePathFinder(PathFinder):
        """
        Makes the package available.
        """

        class ImplicitInitLoader(Loader):
            def create_module(cls, spec: ModuleSpec):
                return cls.load_module(spec.name)

            def exec_module(cls, module: ModuleType):
                pass

            def load_module(cls, fullname: str):
                return ModuleType(fullname)

        @classmethod
        def _is_module(cls, fullname: str):
            return fullname == package_name or fullname.startswith(f"{package_name}.")

        @classmethod
        def _module_path(cls, fullname: str) -> Path:
            assert cls._is_module(fullname)
            return Path("/".join(fullname.split(".")[1:]))

        @classmethod
        def _is_dir(cls, fullname: str) -> bool:
            assert cls._is_module(fullname)
            return cls._module_path(fullname).is_dir()

        @classmethod
        def find_spec(cls, fullname: str, path=None, target=None):
            if cls._is_module(fullname):
                if cls._module_path(fullname).is_dir():
                    return ModuleSpec(
                        name=fullname,
                        loader=cls.ImplicitInitLoader(),
                        is_package=True,
                    )
                else:
                    return super().find_spec(fullname, [package_path])
            else:
                # Allow normal sys.path stuff to handle everything else
                return None

    sys.meta_path.insert(0, PackagePathFinder)  # type: ignore
    try:
        yield None
    finally:
        sys.meta_path.remove(PackagePathFinder)  # type: ignore


@contextmanager
def talon(registry: Registry, *, package: Optional[TalonPackage] = None):
    registry.activate()
    sys.meta_path.insert(0, TalonShimFinder)  # type: ignore
    try:
        if package:
            with talon_package(package):
                yield None
        else:
            yield None
    finally:
        sys.meta_path.remove(TalonShimFinder)  # type: ignore
        Registry.activate(None)
