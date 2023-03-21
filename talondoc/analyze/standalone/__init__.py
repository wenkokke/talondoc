from pathlib import Path
from typing import Optional

from ...registry import Registry
from ...registry.entries.user import UserPackageEntry
from ...util.progress_bar import ProgressBar
from .python import analyse_files as analyse_python_files
from .talon import analyse_files as analyse_talon_files


def _include_file(
    file_path: Path,
    *,
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
) -> bool:
    return (
        not exclude
        or not any(file_path.match(exclude_pattern) for exclude_pattern in exclude)
        or any(file_path.match(include_pattern) for include_pattern in include)
    )


def analyse_package(
    registry: Registry,
    package_dir: Path,
    *,
    package_name: Optional[str] = None,
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
    trigger: tuple[str, ...] = (),
    show_progress: bool = False,
) -> UserPackageEntry:
    # Retrieve or create package entry:
    with registry.package_entry(package_name, package_dir.absolute()) as (
        cached,
        package_entry,
    ):
        if not cached:
            paths = [
                path
                for path in package_entry.path.glob("**/*")
                if _include_file(path, include=include, exclude=exclude)
            ]

            # Analyse Python files
            python_paths = [
                path for path in paths if path.is_file() and path.suffix.endswith(".py")
            ]
            analyse_python_files(
                registry,
                python_paths,
                package_entry,
                trigger=trigger,
                show_progress=show_progress,
            )

            # Analyse Talon files
            talon_paths = [
                path
                for path in paths
                if path.is_file() and path.suffix.endswith(".talon")
            ]
            analyse_talon_files(
                registry,
                talon_paths,
                package_entry,
                show_progress=show_progress,
            )

        return package_entry
