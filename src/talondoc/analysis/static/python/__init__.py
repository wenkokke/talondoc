import importlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec, PathFinder, SourceFileLoader
from pathlib import Path
from types import ModuleType
from typing import ClassVar, Optional, Sequence, cast

from ...._util.logging import getLogger
from ...._util.progress_bar import ProgressBar
from ...registry import Registry
from ...registry import entries as talon
from ...registry.entries.abc import Location
from .shims import ModuleShim, TalonShim

_LOGGER = getLogger(__name__)


class TalonShimFinder(MetaPathFinder):
    """
    Makes the shims available under 'talon' and 'talon_plugins'.
    """

    PACKAGES: ClassVar[tuple[str, ...]] = ("talon", "talon_plugins")

    class TalonShimLoader(Loader):
        def create_module(cls, spec: ModuleSpec) -> ModuleType:
            return cast(ModuleType, cls.load_module(spec.name))

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
    def find_spec(
        cls,
        fullname: str,
        path: Optional[Sequence[str]] = None,
        target: Optional[ModuleType] = None,
    ) -> Optional[ModuleSpec]:
        if cls._is_module(fullname):
            return ModuleSpec(
                name=fullname,
                loader=cls.TalonShimLoader(),
                is_package=True,
            )
        else:
            # Allow normal sys.path stuff to handle everything else
            return None


@contextmanager
def talon_package_shims(package: talon.Package) -> Iterator[None]:
    assert package.location != "builtin"

    package_name = package.name
    package_path = str(package.location.path)

    class PackagePathFinder(PathFinder):
        """
        Makes the package available.
        """

        class ImplicitInitLoader(Loader):
            def create_module(cls, spec: ModuleSpec):
                return cls.load_module(spec.name)

            def exec_module(cls, _module: ModuleType):
                pass

            def load_module(cls, fullname: str):
                return ModuleType(fullname)

        @classmethod
        def _is_module(cls, fullname: str) -> bool:
            return fullname == package_name or fullname.startswith(f"{package_name}.")

        @classmethod
        def _module_path(cls, fullname: str) -> Path:
            assert cls._is_module(fullname)
            return Path(package_path, *fullname.split(".")[1:])

        @classmethod
        def _is_subpackage(cls, fullname: str) -> bool:
            return cls._is_module(fullname) and cls._module_path(fullname).is_dir()

        @classmethod
        def find_spec(cls, fullname: str, path=None, _target=None):
            if cls._is_module(fullname):
                if cls._is_subpackage(fullname):
                    module_spec = ModuleSpec(
                        name=fullname, loader=cls.ImplicitInitLoader(), is_package=True
                    )
                    submodule_search_location = str(cls._module_path(fullname))
                    if not module_spec.submodule_search_locations:
                        module_spec.submodule_search_locations = []
                    module_spec.submodule_search_locations.append(
                        submodule_search_location
                    )
                    return module_spec
                else:
                    path = str(cls._module_path(fullname).with_suffix(".py"))
                    module_spec = ModuleSpec(
                        name=fullname,
                        loader=SourceFileLoader(fullname, path),
                        origin=path,
                        is_package=False,
                    )
                    module_spec.has_location = True
                    return module_spec
            else:
                # Allow normal sys.path stuff to handle everything else
                return None

    sys.meta_path.insert(0, PackagePathFinder)
    try:
        yield None
    finally:
        sys.meta_path.remove(PackagePathFinder)


@contextmanager
def talon_shims(registry: Registry, *, package: Optional[talon.Package] = None):
    sys.meta_path.insert(0, TalonShimFinder)
    try:
        if package:
            with talon_package_shims(package):
                yield None
        else:
            yield None
    finally:
        sys.meta_path.remove(TalonShimFinder)


def analyse_file(registry: Registry, path: Path, package: talon.Package) -> None:
    # Retrieve or create file entry:
    file = talon.File(
        location=Location.from_path(path),
        parent_name=package.name,
    )
    registry.register(file)
    # Process file (passes control to talondoc.analyzer.python.shims):
    module_name = ".".join([package.name, *path.with_suffix("").parts])
    importlib.import_module(name=module_name, package=package.name)


def analyse_files(
    registry: Registry,
    paths: Sequence[Path],
    package: talon.Package,
    *,
    trigger: tuple[str, ...] = (),
    show_progress: bool = False,
    continue_on_error: bool = True,
) -> None:
    assert package.location != "builtin"
    # Retrieve or create package entry:
    with talon_shims(registry, package=package):
        bar = ProgressBar(total=len(paths), show=show_progress)
        for file_path in paths:
            file_path = file_path.relative_to(package.location.path)
            try:
                bar.step(f" {file_path}")
                analyse_file(registry, file_path, package)
            except Exception as e:
                if continue_on_error:
                    raise e
                else:
                    _LOGGER.exception(e)

        # Trigger callbacks:
        for event_code in trigger:
            callbacks = registry.lookup(talon.Callback, event_code)
            if callbacks is not None:
                for callback in callbacks:
                    callback.function()
