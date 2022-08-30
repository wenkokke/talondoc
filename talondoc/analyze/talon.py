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
from . import Registry
from ..types import *


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
            talon_file_entry.matches = declaration
        elif isinstance(declaration, TalonCommandDeclaration):
            # Register command:
            command_entry = CommandEntry(file=talon_file_entry, ast=declaration)
            talon_file_entry.commands.append(command_entry)
            registry.register(command_entry)
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

    return talon_file_entry
