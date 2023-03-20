import importlib
from collections.abc import Sequence
from pathlib import Path
from typing import Optional, cast

from tree_sitter_talon import (
    ParseError,
    TalonAssignmentStatement,
    TalonBlock,
    TalonCommandDeclaration,
    TalonDeclarations,
    TalonMatches,
    TalonSettingsDeclaration,
    TalonSourceFile,
    TalonTagImportDeclaration,
    parse_file,
)

from ..registry import Registry
from ..registry.entries.user import (
    UserCallbackEntry,
    UserCommandEntry,
    UserFileEntry,
    UserPackageEntry,
    UserPythonFileEntry,
    UserSettingEntry,
    UserTalonFileEntry,
)
from ..util.logging import getLogger
from ..util.progress_bar import ProgressBar
from .shims import talon

_LOGGER = getLogger(__name__)


def include_file(
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
            with talon(registry, package=package_entry):
                files = list(package_entry.path.glob("**/*"))
                bar = ProgressBar(total=len(files), show=show_progress)
                for file_path in files:
                    file_path = file_path.relative_to(package_entry.path)
                    if include_file(file_path, include=include, exclude=exclude):
                        try:
                            if file_path.match("*.py"):
                                bar.step(f" {file_path}")
                                analyse_python_file(registry, file_path, package_entry)
                            elif file_path.match("*.talon"):
                                bar.step(f" {file_path}")
                                analyse_talon_file(registry, file_path, package_entry)
                            else:
                                bar.step()
                        except ParseError as e:
                            _LOGGER.exception(e)

                # Trigger callbacks:
                for event_code in trigger:
                    callback_entries = registry.lookup("callback", event_code)
                    if callback_entries:
                        for callback_entry in callback_entries:
                            callback_entry.func()

        return package_entry


def analyse_talon_file(
    registry: Registry, path: Path, package: UserPackageEntry
) -> UserTalonFileEntry:
    # Retrieve or create file entry:
    with registry.file_entry(UserTalonFileEntry, package, path) as (cached, file_entry):
        # Process file:
        if not cached:
            ast = parse_file(package.path / path, raise_parse_error=True)
            assert isinstance(ast, TalonSourceFile)
            for child in ast.children:
                if isinstance(child, TalonMatches):
                    # Register matches:
                    assert file_entry.matches is None
                    file_entry.matches = child
                elif isinstance(child, TalonDeclarations):
                    for declaration in child.children:
                        if isinstance(declaration, TalonCommandDeclaration):
                            # Register command:
                            command_entry = UserCommandEntry(
                                parent=file_entry, ast=declaration
                            )
                            registry.register(command_entry)
                        elif isinstance(declaration, TalonSettingsDeclaration):
                            # Register settings:
                            for statement in declaration.right.children:
                                if isinstance(statement, TalonAssignmentStatement):
                                    setting_use_entry = UserSettingEntry(
                                        name=statement.left.text,
                                        parent=file_entry,
                                        value=statement.right,
                                    )
                                    registry.register(setting_use_entry)
                        elif isinstance(declaration, TalonTagImportDeclaration):
                            # Register tag import:
                            # TODO: add use entries
                            pass

        return file_entry


def analyse_python_file(
    registry: Registry, path: Path, package: UserPackageEntry
) -> UserPythonFileEntry:
    # Retrieve or create file entry:
    with registry.file_entry(UserPythonFileEntry, package, path) as (
        _cached,
        file_entry,
    ):
        try:
            # Process file (passes control to talondoc.shims.*):
            module_name = ".".join([package.name, *path.with_suffix("").parts])
            importlib.import_module(name=module_name, package=package.name)
            return file_entry
        except ModuleNotFoundError as e:
            raise e
