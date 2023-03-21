import importlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec, PathFinder, SourceFileLoader
from pathlib import Path
from types import ModuleType
from typing import ClassVar, Optional, Sequence, Union

from ....registry import Registry
from ....registry.entries.user import UserPackageEntry, UserPythonFileEntry
from ....util.logging import getLogger
from ....util.progress_bar import ProgressBar
from .shims import ModuleShim, TalonShim

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


AnyTalonPackage = Union[tuple[str, Union[str, Path]], UserPackageEntry]


@contextmanager
def talon_package_shims(package: AnyTalonPackage) -> Iterator[None]:
    if isinstance(package, UserPackageEntry):
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
            return Path(package_path, *fullname.split(".")[1:])

        @classmethod
        def _is_subpackage(cls, fullname: str) -> bool:
            return cls._is_module(fullname) and cls._module_path(fullname).is_dir()

        @classmethod
        def find_spec(cls, fullname: str, path=None, target=None):
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

    sys.meta_path.insert(0, PackagePathFinder)  # type: ignore
    try:
        yield None
    finally:
        sys.meta_path.remove(PackagePathFinder)  # type: ignore


@contextmanager
def talon_shims(registry: Registry, *, package: Optional[AnyTalonPackage] = None):
    registry.activate()
    sys.meta_path.insert(0, TalonShimFinder)  # type: ignore
    try:
        if package:
            with talon_package_shims(package):
                yield None
        else:
            yield None
    finally:
        sys.meta_path.remove(TalonShimFinder)  # type: ignore
        Registry.activate(None)


def analyse_file(
    registry: Registry, path: Path, package: UserPackageEntry
) -> UserPythonFileEntry:
    # Retrieve or create file entry:
    with registry.file_entry(UserPythonFileEntry, package, path) as (
        _cached,
        file_entry,
    ):
        try:
            # Process file (passes control to talondoc.analyze.standalone.python.shims):
            module_name = ".".join([package.name, *path.with_suffix("").parts])
            importlib.import_module(name=module_name, package=package.name)
            return file_entry
        except ModuleNotFoundError as e:
            raise e


def analyse_files(
    registry: Registry,
    paths: Sequence[Path],
    package: UserPackageEntry,
    *,
    trigger: tuple[str, ...] = (),
    show_progress: bool = False,
) -> None:
    # Retrieve or create package entry:
    with registry.as_active_package_entry(package):
        with talon_shims(registry, package=package):
            bar = ProgressBar(total=len(paths), show=show_progress)
            for path in paths:
                path = path.relative_to(package.path)
                try:
                    bar.step(f" {path}")
                    analyse_file(registry, path, package)
                except Exception as e:
                    _LOGGER.exception(e)

            # Trigger callbacks:
            for event_code in trigger:
                callback_entries = registry.lookup("callback", event_code)
                if callback_entries:
                    for callback_entry in callback_entries:
                        callback_entry.func()
