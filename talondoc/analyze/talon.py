from tree_sitter_talon import (
    TalonAssignmentStatement,
    TalonBlock,
    TalonCommandDeclaration,
    TalonMatches,
    TalonSettingsDeclaration,
    TalonSourceFile,
    TalonTagImportDeclaration,
    parse_file,
)

from ..types import *
from . import Registry


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
