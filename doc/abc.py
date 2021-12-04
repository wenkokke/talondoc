from contextlib import AbstractContextManager
from talon import Module, actions, registry
from talon.scripting.context import Context
from typing import *
from user.cheatsheet.doc.talon_script.describe import (
    describe_context_name,
    describe_command,
)


# Abstract classes for printing cheatsheet document
class Cell(AbstractContextManager):
    def line(self):
        """Inserts a line."""


class Row(AbstractContextManager):
    def cell(
        self, contents: Optional[str] = None, verbatim: bool = False
    ) -> Optional[Cell]:
        """If the first argument is provided, a single line cell is created. Otherwise, a cell is created and returned."""


class Table(AbstractContextManager):
    def row(self) -> Row:
        """Creates a row."""


class Section(AbstractContextManager):
    def table(self, title: str, cols: int, anchor: Optional[str] = None) -> Table:
        """Creates a table with <cols> columns."""

    def list(self, list_name: str) -> None:
        """Create a table for a Talon list."""
        with self.table(title=list_name, cols=2, anchor="talon-list") as table:
            for key, value in registry.lists[list_name][0].items():
                with table.row() as row:
                    row.cell(key)
                    row.cell(value, verbatim=True)

    def formatters(self) -> None:
        """Create table for the talon formatters list."""
        with self.table(
            title="user.formatters", cols=2, anchor="talon-formatters"
        ) as table:
            for key, _ in registry.lists["user.formatters"][0].items():
                with table.row() as row:
                    example = actions.user.formatted_text(
                        f"example of formatting with {key}", key
                    )
                    row.cell(key)
                    row.cell(example, verbatim=True)

    def context(self, context_name: str, context: Context) -> None:
        """Write each command and its implementation as a table"""
        if context.commands:
            with self.table(
                title=describe_context_name(context_name),
                cols=2,
                anchor="talon-context",
            ) as table:
                for command in context.commands.values():
                    with table.row() as row:
                        row.cell(command.rule.rule)
                        docs = describe_command(command)
                        impl = "\n".join(map(str.strip, command.target.code.splitlines()))
                        if docs is not None:
                            with row.cell() as cell:
                                for line in docs:
                                    cell.line(line.strip().capitalize())
                        else:
                            row.cell(impl, verbatim=True)
        else:
            pass
            # print(f"{context_name}: Defines no commands")


class Doc(AbstractContextManager):
    def section(self, title: str, cols: int, anchor: Optional[str] = None) -> Section:
        """Create a new section."""
