from pathlib import Path
from typing import Sequence

from tree_sitter_talon import (
    ParseError,
    TalonAssignmentStatement,
    TalonCommandDeclaration,
    TalonDeclarations,
    TalonMatches,
    TalonSettingsDeclaration,
    TalonSourceFile,
    TalonTagImportDeclaration,
    parse_file,
)

from ...registry import Registry
from ...registry.entries.user import (
    UserCommandEntry,
    UserPackageEntry,
    UserSettingEntry,
    UserTalonFileEntry,
)
from ...util.logging import getLogger
from ...util.progress_bar import ProgressBar

_LOGGER = getLogger(__name__)


def analyse_file(
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


def analyse_files(
    registry: Registry,
    paths: Sequence[Path],
    package: UserPackageEntry,
    *,
    show_progress: bool = False,
) -> None:
    # Retrieve or create package entry:
    with registry.as_active_package_entry(package):
        bar = ProgressBar(total=len(paths), show=show_progress)
        for path in paths:
            path = path.relative_to(package.path)
            try:
                bar.step(f" {path}")
                analyse_file(registry, path, package)
            except ParseError as e:
                _LOGGER.exception(e)
