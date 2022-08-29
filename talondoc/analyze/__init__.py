from functools import singledispatchmethod
from typing import cast
from tree_sitter_talon import (
    parse_file,
    TalonAssignmentStatement,
    TalonBlock,
    TalonCommandDeclaration,
    TalonMatches,
    TalonSettingsDeclaration,
    TalonSourceFile,
    TalonTagImportDeclaration,
)
from ..types import *


class Registry:
    @singledispatchmethod
    def register_entry(self, entry: ObjectEntry):
        """
        Register an object entry.
        """

    @singledispatchmethod
    def register_use(self, entry: ObjectEntry, entry_used: ObjectEntry):
        """
        Register an object entry used by another object entry.
        """


def analyse_package(registry: Registry, package_root: pathlib.Path) -> PackageEntry:
    package_entry = PackageEntry(path=package_root)
    for path in package_root.glob("**/*"):
        if path.match("*.talon"):
            # Analyze Python file:
            pass
        elif path.match("*.py"):
            # Analyze Talon file:
            file_entry = analyse_talon_file(registry, path, package_entry)
            package_entry.files.append(file_entry)

    # Register package:
    registry.register_entry(package_entry)
    return package_entry


def analyse_talon_file(
    registry: Registry, talon_file: pathlib.Path, package_entry: PackageEntry
) -> TalonFileEntry:
    talon_file_entry = TalonFileEntry(path=talon_file.relative_to(package_entry.path))
    source_file = cast(TalonSourceFile, parse_file(talon_file, raise_parse_error=True))
    for declaration in source_file.children:
        if isinstance(declaration, TalonMatches):
            # Register matches:
            talon_file_entry.matches = declaration
        elif isinstance(declaration, TalonCommandDeclaration):
            # Register command:
            command_entry = CommandEntry(file=talon_file_entry, ast=declaration)
            talon_file_entry.commands.append(command_entry)
            registry.register_entry(command_entry)
            registry.register_use(talon_file_entry, command_entry)
        elif isinstance(declaration, TalonSettingsDeclaration):
            # Register settings:
            for child in declaration.children:
                if isinstance(child, TalonBlock):
                    for statement in child.children:
                        if isinstance(statement, TalonAssignmentStatement):
                            setting_entry = SettingEntry(
                                name=statement.left.text,
                                value=statement.right,
                            )
                            talon_file_entry.settings.append(setting_entry)
                            registry.register_use(talon_file_entry, setting_entry)
        elif isinstance(declaration, TalonTagImportDeclaration):
            # Register tag import:
            tag_entry = TagEntry(name=declaration.tag.text)
            talon_file_entry.tag_imports.append(tag_entry)
            registry.register_use(talon_file_entry, tag_entry)

    # Register file:
    registry.register_entry(talon_file_entry)
    return talon_file_entry
