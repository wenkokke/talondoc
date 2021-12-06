from __future__ import annotations
from contextlib import AbstractContextManager
from talon import Module, actions, registry
from talon.scripting.context import Context  # type: ignore
from typing import *
from user.cheatsheet.doc.talon_script.describe import Describe


# Abstract classes for printing cheatsheet document


class Row(AbstractContextManager):
    def cell(self, contents: str, verbatim: bool = False):
        """Writes a cell to the row."""


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
                title=Describe.context_name(context_name),
                cols=2,
                anchor="talon-context",
            ) as table:
                for command in context.commands.values():
                    with table.row() as row:
                        row.cell(command.rule.rule)
                        docs = Describe.command(command)
                        impl = "\n".join(line.strip() for line in command.target.code.splitlines())
                        if docs is not None:
                            row.cell(docs)
                        else:
                            row.cell(impl, verbatim=True)
        else:
            pass


class Doc(AbstractContextManager):
    def section(self, title: str, cols: int, anchor: Optional[str] = None) -> Section:
        """Create a new section."""
