import importlib
import pathlib
from typing import Optional

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
    PackageEntry,
    PythonFileEntry,
    SettingValueEntry,
    TagImportEntry,
    TalonFileEntry,
)
from .registry import Registry
from .shims import talon

_LOGGER = getLogger(__name__)


def include_file(
    file_path: pathlib.Path,
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
    package_dir: pathlib.Path,
    *,
    package_name: Optional[str] = None,
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
    trigger: tuple[str, ...] = (),
    show_progress: bool = False,
) -> PackageEntry:

    # Retrieve or create package entry:
    def _get_package_entry() -> PackageEntry:
        new_package_entry = PackageEntry(name=package_name, path=package_dir.absolute())
        for old_package_entry in registry.packages.values():
            if (
                old_package_entry.name == new_package_entry.name
                and old_package_entry.path == new_package_entry.path
            ):
                return old_package_entry
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
            callback_entries = registry.lookup(f"callback:{event_code}")
            if callback_entries is not None:
                assert isinstance(callback_entries, list)
                for callback_entry in callback_entries:
                    assert isinstance(callback_entry, CallbackEntry)
                    callback_entry.callback()

    return package_entry


def analyse_talon_file(
    registry: Registry, talon_file_path: pathlib.Path, package_entry: PackageEntry
) -> TalonFileEntry:

    # Retrieve or create file entry:
    def _get_file_entry() -> TalonFileEntry:
        new_file_entry = TalonFileEntry(package=package_entry, path=talon_file_path)
        old_file_entry = registry.files.get(new_file_entry.name, None)
        if old_file_entry:
            assert isinstance(old_file_entry, TalonFileEntry)
            return old_file_entry
        else:
            registry.register(new_file_entry)
            return new_file_entry

    talon_file_entry = _get_file_entry()

    # Process file:
    if (
        talon_file_entry.mtime is not None
        and talon_file_path.stat().st_mtime > talon_file_entry.mtime
    ):
        ast = parse_file(package_entry.path / talon_file_path, raise_parse_error=True)
        assert isinstance(ast, TalonSourceFile)
        for declaration in ast.children:
            if isinstance(declaration, TalonMatches):
                # Register matches:
                assert talon_file_entry.matches is None
                talon_file_entry.matches = declaration
            elif isinstance(declaration, TalonCommandDeclaration):
                # Register command:
                command_entry = CommandEntry(file=talon_file_entry, ast=declaration)
                registry.register(command_entry)
            elif isinstance(declaration, TalonSettingsDeclaration):
                # Register settings:
                for child in declaration.children:
                    if isinstance(child, TalonBlock):
                        for statement in child.children:
                            if isinstance(statement, TalonAssignmentStatement):
                                setting_use_entry = SettingValueEntry(
                                    name=statement.left.text,
                                    file_or_module=talon_file_entry,
                                    value=statement.right,
                                )
                                registry.register(setting_use_entry)
            elif isinstance(declaration, TalonTagImportDeclaration):
                # Register tag import:
                tag_entry = TagImportEntry(
                    name=declaration.tag.text, file_or_module=talon_file_entry
                )
                registry.register(tag_entry)

    return talon_file_entry


def analyse_python_file(
    registry: Registry, python_file_path: pathlib.Path, package_entry: PackageEntry
) -> PythonFileEntry:

    # Retrieve or create file entry:
    def _get_file_entry() -> PythonFileEntry:
        new_file_entry = PythonFileEntry(package=package_entry, path=python_file_path)
        old_file_entry = registry.files.get(new_file_entry.name, None)
        if old_file_entry:
            assert isinstance(old_file_entry, PythonFileEntry)
            return old_file_entry
        else:
            registry.register(new_file_entry)
            return new_file_entry

    python_file_entry = _get_file_entry()

    # Process file (passes control to talondoc.shims.*):
    module_name = ".".join(
        [package_entry.name, *python_file_path.with_suffix("").parts]
    )
    importlib.import_module(name=module_name, package=package_entry.name)

    return python_file_entry
