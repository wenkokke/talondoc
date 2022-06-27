from __future__ import annotations
from contextlib import AbstractContextManager
from talon import actions, registry
from talon.scripting.context import Context  # type: ignore
from typing import *
from user.cheatsheet.doc.talon_script.describe import Describe
import re

# Abstract classes for printing cheatsheet document

class Row(AbstractContextManager):
    def cell(self, contents: str, **kwargs):
        """
        Writes a cell to the row.
        """


class Table(AbstractContextManager):
    def row(self, **kwargs) -> Row:
        """
        Creates a row.
        """


class Section(AbstractContextManager):
    def table(self, title: str, **kwargs) -> Table:
        """Creates a table with <cols> columns."""

    def list(self, list_name: str, **kwargs) -> None:
        """
        Create a table for a Talon list.

        Args:
            list_name: The name of the list.
            **table_title: The table title.
        """

        # Set the default title based on the list name:
        kwargs["title"] = kwargs.get("title", list_name)

        with self.table(cols=2, **kwargs) as table:
            for key, value in registry.lists[list_name][0].items():
                with table.row(**kwargs) as row:
                    row.cell(key, **kwargs)
                    row.cell(value, **kwargs)

    def formatters(self, **kwargs) -> None:
        """
        Create table for the talon formatters list.

        Args:
            **list_names: The names of the formatters lists. Defaults to 'user.formatters'.
            **formatted_text: The name of the formatter function. Defaults to 'actions.user.formatted_text'.
            **table_title: The table title.
            **context_name: The Talon context name. Used to generate the table title if the **table_title keyword is not given.
        """

        # Set the default list name and formatting function:
        list_names = kwargs.get("list_names", ("user.formatters",))
        formatted_text = kwargs.get("formatted_text", actions.user.formatted_text)
        for list_name in list_names:
            with self.table(cols=2, title=list_name, **kwargs) as table:
                if list_name in registry.lists:
                    items = registry.lists[list_name]
                    if isinstance(items, list):
                        items = items[0]
                    for key, val in items.items():
                        with table.row(**kwargs) as row:
                            example = formatted_text(f"example of formatting with {key}", val)
                            row.cell(key, **kwargs)
                            row.cell(example, **kwargs)

    def context(self, context: Context, **kwargs) -> None:
        """
        Write each command and its implementation as a table.

        Args:
            context: The Talon context object.
            **table_title: The table title.
            **context_name: The Talon context name. Used to generate the table title if the **table_title keyword is not given.
        """
        if context.commands:
            # Set the default context name:
            # Set the default table title based on the context name:
            if 'context_name' in kwargs:
                kwargs["title"] = kwargs.get("title", \
                    Describe.context_name(kwargs["context_name"]))

            # Create table to describe context:
            with self.table(cols=2, **kwargs) as table:
                for command in context.commands.values():
                    with table.row(**kwargs) as row:
                        row.cell(Describe.command_rule(command), non_breaking=True, **kwargs)
                        docs = Describe.command(command)
                        impl = Describe.command_impl(command)
                        if docs is not None:
                            row.cell(docs, **kwargs)
                        else:
                            row.cell(impl, css_classes='talon-script', **kwargs)
        else:
            pass


class Doc(AbstractContextManager):
    def section(self, **kwargs) -> Section:
        """
        Create a new section.

        Args:
            **section_title: The section title.
        """
