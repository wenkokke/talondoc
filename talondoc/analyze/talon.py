import pathlib

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

from .entries import (
    CommandEntry,
    PackageEntry,
    SettingValueEntry,
    TagImportEntry,
    TalonFileEntry,
)
from . import Registry


