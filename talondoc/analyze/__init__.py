import pathlib
import typing

from ..entries import CallbackEntry, FileEntry, PackageEntry
from ..shims import talon_shims
from .python import analyse_python_file, python_package
from .registry import Registry
from .talon import analyse_talon_file
from tree_sitter_talon import ParseError

from ..util.logging import getLogger

_logger = getLogger(__name__)


def analyse_package(
    registry: Registry,
    package_root: pathlib.Path,
    *,
    name: typing.Optional[str] = None,
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
    trigger: tuple[str, ...] = (),
) -> PackageEntry:
    def _include_file(
        file_path: pathlib.Path,
    ) -> bool:
        return (
            not exclude
            or not any(file_path.match(exclude_pattern) for exclude_pattern in exclude)
            or any(file_path.match(include_pattern) for include_pattern in include)
        )

    package_entry = PackageEntry(name=name, path=package_root.absolute())
    with talon_shims(registry):
        with python_package(package_entry):
            for file_path in package_entry.path.glob("**/*"):
                file_path = file_path.relative_to(package_entry.path)
                if _include_file(file_path):
                    try:
                        analyse_file(registry, file_path, package_entry)
                    except ParseError as e:
                        _logger.exception(e)

            # Register package:
            registry.register(package_entry)

            # Trigger callbacks:
            for event_code in trigger:
                callback_entries = typing.cast(
                    list[CallbackEntry],
                    registry.lookup(f"callback:{event_code}"),
                )
                for callback_entry in callback_entries:
                    callback_entry.callback()

    return package_entry


def analyse_file(
    registry: Registry, file_path: pathlib.Path, package_entry: PackageEntry
) -> typing.Optional[FileEntry]:
    if file_path.match("*.py"):
        return analyse_python_file(registry, file_path, package_entry)
    elif file_path.match("*.talon"):
        return analyse_talon_file(registry, file_path, package_entry)
    else:
        return None
