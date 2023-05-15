from pathlib import Path
from typing import Optional

from ..registry import Registry
from ..registry.entries import Package
from ..registry.entries.abc import Location
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
    continue_on_error: bool = True,
) -> None:
    # Activate the registry:
    registry.activate()

    # Retrieve or create package entry:
    package = Package(
        name=package_name or package_dir.parts[-1],
        location=Location.from_path(package_dir.absolute()),
    )
    registry.register(package)
    paths = [
        path
        for path in package.location.path.glob("**/*")
        if _include_file(path, include=include, exclude=exclude)
    ]

    # Analyse Python files
    python_paths = [
        path for path in paths if path.is_file() and path.suffix.endswith(".py")
    ]
    analyse_python_files(
        registry,
        python_paths,
        package,
        trigger=trigger,
        show_progress=show_progress,
        continue_on_error=continue_on_error,
    )

    # Analyse Talon files
    talon_paths = [
        path for path in paths if path.is_file() and path.suffix.endswith(".talon")
    ]
    analyse_talon_files(
        registry,
        talon_paths,
        package,
        show_progress=show_progress,
    )

    # Deactivate the registry:
    registry.deactivate()
