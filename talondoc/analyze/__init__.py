import importlib
import pathlib
import typing

from .shims import talon, talon_package
from .registry import Registry
from tree_sitter_talon import (
    TalonAssignmentStatement,
    TalonBlock,
    TalonCommandDeclaration,
    TalonMatches,
    TalonSettingsDeclaration,
    TalonSourceFile,
    TalonTagImportDeclaration,
    parse_file,
    ParseError,
)

from .entries import (
    CommandEntry,
    PackageEntry,
    SettingValueEntry,
    TagImportEntry,
    TalonFileEntry,
    CallbackEntry,
    FileEntry,
    PythonFileEntry,
    TalonFileEntry,
)

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

    # Register package:
    package_entry = PackageEntry(name=name, path=package_root.absolute())
    registry.register(package_entry)

    with talon(registry, package=package_entry):
        for file_path in package_entry.path.glob("**/*"):
            file_path = file_path.relative_to(package_entry.path)
            if _include_file(file_path):
                try:
                    analyse_file(registry, file_path, package_entry)
                except ParseError as e:
                    _logger.exception(e)

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


def analyse_talon_file(
    registry: Registry, talon_file_path: pathlib.Path, package_entry: PackageEntry
) -> TalonFileEntry:

    # Register file:
    talon_file_entry = TalonFileEntry(package=package_entry, path=talon_file_path)
    registry.register(talon_file_entry)

    # Process file:
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
    registry: Registry, python_file: pathlib.Path, package_entry: PackageEntry
) -> PythonFileEntry:

    # Register file:
    python_file_entry = PythonFileEntry(package=package_entry, path=python_file)
    registry.register(python_file_entry)

    # Process file (passes control to talondoc.shims.*):
    module_name = ".".join([package_entry.name, *python_file.with_suffix("").parts])
    importlib.import_module(name=module_name, package=package_entry.name)

    return python_file_entry
