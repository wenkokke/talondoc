from pathlib import Path
from typing import Iterator, List, Optional, Sequence

from tree_sitter_talon import (
    ParseError,
    TalonAssignmentStatement,
    TalonCommandDeclaration,
    TalonDeclaration,
    TalonDeclarations,
    TalonMatch,
    TalonMatches,
    TalonSettingsDeclaration,
    TalonSourceFile,
    TalonTagImportDeclaration,
    parse_file,
)

from ..._util.logging import getLogger
from ..._util.progress_bar import ProgressBar
from .. import Registry
from .. import entries as talon

_LOGGER = getLogger(__name__)


def _TalonSourceFile_get_matches(ast: TalonSourceFile) -> Iterator[talon.Match]:
    for child in ast.children:
        if isinstance(child, TalonMatches):
            for match in child.children:
                if isinstance(match, TalonMatch):
                    yield match


def _TalonSourceFile_get_declarations(
    ast: TalonSourceFile,
) -> Iterator[TalonDeclaration]:
    for child in ast.children:
        if isinstance(child, TalonDeclarations):
            yield from child.children


def analyse_file(registry: Registry, path: Path, package: talon.Package) -> None:
    assert package.location != "builtin"
    # Create a file entry:
    file = talon.File(
        location=talon.Location.from_path(path),
        parent_name=package.name,
    )
    registry.register(file)

    # Parse file:
    ast = parse_file(package.location.path / path, raise_parse_error=True)
    assert isinstance(ast, TalonSourceFile)

    # Create a context entry:
    context = talon.Context(
        matches=list(_TalonSourceFile_get_matches(ast)),
        index=len(file.contexts),
        description=ast.get_docstring(),
        location=file.location,
        parent_name=file.name,
    )
    file.contexts.append(context.name)
    registry.register(context)

    # Process declarations:
    for declaration in _TalonSourceFile_get_declarations(ast):
        if isinstance(declaration, TalonCommandDeclaration):
            # Register command:
            command = talon.Command(
                rule=declaration.left,
                script=declaration.right,
                index=len(context.commands),
                description=declaration.get_docstring(),
                location=talon.Location.from_ast(context.location.path, declaration),
                parent_name=context.name,
            )
            context.commands.append(command.name)
            registry.register(command)
        elif isinstance(declaration, TalonSettingsDeclaration):
            # Register settings:
            for statement in declaration.right.children:
                if isinstance(statement, TalonAssignmentStatement):
                    registry.register(
                        talon.Setting(
                            value=statement.right,
                            value_type_hint=None,
                            name=statement.left.text,
                            description=None,
                            location=talon.Location.from_ast(
                                context.location.path, statement
                            ),
                            parent_name=context.name,
                            parent_type=talon.Context,
                        )
                    )
        elif isinstance(declaration, TalonTagImportDeclaration):
            # Register tag import:
            # TODO: add use entries
            pass


def analyse_files(
    registry: Registry,
    paths: Sequence[Path],
    package: talon.Package,
    *,
    show_progress: bool = False,
) -> None:
    assert package.location != "builtin"
    # Retrieve or create package entry:
    bar = ProgressBar(total=len(paths), show=show_progress)
    for path in paths:
        path = path.relative_to(package.location.path)
        try:
            bar.step(f" {path}")
            analyse_file(registry, path, package)
        except ParseError as e:
            _LOGGER.exception(e)
