import importlib
from collections.abc import Sequence
from pathlib import Path
from typing import Optional, cast

from tree_sitter_talon import (
    ParseError,
    TalonAssignmentStatement,
    TalonBlock,
    TalonCommandDeclaration,
    TalonMatches,
    TalonSettingsDeclaration,
    TalonSourceFile,
    TalonTagImportDeclaration,
    parse_file,
)

from ..util.logging import getLogger
from ..util.progress_bar import ProgressBar
from .entries import (
    CallbackEntry,
    CommandEntry,
    FileEntry,
    PackageEntry,
    PythonFileEntry,
    SettingEntry,
    TalonFileEntry,
)
from .registry import Registry
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
) -> PackageEntry:

    # Retrieve or create package entry:
    def _get_package_entry() -> PackageEntry:
        patckage_path = package_dir.absolute()
        for old_package_entry in registry.packages.values():
            if (
                old_package_entry.name == package_name
                and old_package_entry.path == patckage_path
            ):
                _LOGGER.debug(f"[talondoc] skip package '{package_dir}'")
                registry.active_package_entry = old_package_entry
                return old_package_entry
        new_package_entry = PackageEntry(name=package_name, path=patckage_path)
        registry.register(new_package_entry)
        return new_package_entry

    package_entry = _get_package_entry()

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
            callback_entries = registry.lookup(CallbackEntry, event_code)
            if callback_entries:
                for callback_entry in callback_entries:
                    callback_entry.func()

    return package_entry


def analyse_talon_file(
    registry: Registry, path: Path, package: PackageEntry
) -> TalonFileEntry:

    # Retrieve or create file entry:
    file_entry = registry.file_entry(TalonFileEntry, package, path)

    # Process file, if newer:
    if file_entry.mtime is not None and path.stat().st_mtime > file_entry.mtime:
        ast = parse_file(package.path / path, raise_parse_error=True)
        assert isinstance(ast, TalonSourceFile)
        for declaration in ast.children:
            if isinstance(declaration, TalonMatches):
                # Register matches:
                assert file_entry.matches is None
                file_entry.matches = declaration
            elif isinstance(declaration, TalonCommandDeclaration):
                # Register command:
                command_entry = CommandEntry(parent=file_entry, ast=declaration)
                registry.register(command_entry)
            elif isinstance(declaration, TalonSettingsDeclaration):
                # Register settings:
                for child in declaration.children:
                    if isinstance(child, TalonBlock):
                        for statement in child.children:
                            if isinstance(statement, TalonAssignmentStatement):
                                setting_use_entry = SettingEntry(
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
    registry: Registry, path: Path, package: PackageEntry
) -> PythonFileEntry:

    # Retrieve or create file entry:
    file_entry = registry.file_entry(PythonFileEntry, package, path)

    # Process file (passes control to talondoc.shims.*):
    module_name = ".".join([package.name, *path.with_suffix("").parts])
    importlib.import_module(name=module_name, package=package.name)

    return file_entry
