from abc import ABC
from contextlib import AbstractContextManager, contextmanager, nullcontext
from talon import Module, actions, registry
from talon.scripting.context import Context
from talon.scripting.talon_script import *
from talon.scripting.types import CommandImpl
from io import TextIOWrapper
from typing import *

import os
import re
import sys

mod = Module()


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
    def title(self, title: str):
        """Set the table title."""

    def row(self) -> Row:
        """Creates a row."""


class Doc(AbstractContextManager):
    def title(self, title: str):
        """Set the document title."""

    def table(self) -> Table:
        """Creates a table."""

    def list(self, list_name: str) -> None:
        """Create a table for a Talon list."""
        with self.table() as table:
            table.title(list_name)
            for key, value in registry.lists[list_name][0].items():
                with table.row() as row:
                    row.cell(key)
                    row.cell(value)

    def formatters(self) -> None:
        """Create table for the talon formatters list."""
        with self.table() as table:
            table.title("user.formatters")
            for key, _ in registry.lists["user.formatters"][0].items():
                with table.row() as row:
                    example = actions.user.formatted_text(
                        f"example of formatting with {key}", key
                    )
                    row.cell(key)
                    row.cell(example)

    def context(self, context_name: str, context: Context) -> None:
        """Write each command and its implementation as a table"""
        if context.commands:
            with self.table() as table:
                table.title(describe_context_name(context_name))
                for command in context.commands.values():
                    with table.row() as row:
                        row.cell(command.rule.rule)
                        docs = describe_command(command)
                        impl = describe_command_implementation(command)
                        if docs:
                            with row.cell() as cell:
                                for line in docs:
                                    cell.line(line.strip().capitalize())
                        else:
                            row.cell(impl, verbatim=True)
        else:
            print(f"{context_name}: Defines no commands")


# Logic for describing commands


"""The type of documentation strings:
If the value is None, there is no documentation.
If the value is a string, it represents documentation which can be composed horizontally.
Otherwise, if the value is a list of strings, it represents documentation which can be composed vertically."""
DocString = Union[None, str, list[str]]


def is_simple(doc: DocString) -> bool:
    """Check whether a document string can be composed horizontally"""
    return type(doc) == str


action_custom_describe: Dict[str, Callable[[tuple[DocString]], DocString]] = {
    "key": lambda args: "Press {}".format(*args),
    "insert": lambda args: ['"{}"'.format(*args)],
    "auto_insert": lambda args: ['"{}"'.format(*args)],
    "sleep": lambda _: [],
    "edit.selected_text": lambda _: "the selected text",
    "user.vscode": lambda args: ["Ask VSCode to run {}".format(*args)],
    "user.idea": lambda args: ["Ask Jetbrains IDE to run {}".format(*args)],
    "user.formatted_text": lambda args: "{} (formatted with {})".format(*args),
}


def describe_action(action_name: str, args: tuple[DocString]) -> DocString:
    """Return the doc string for the action, if available"""
    global action_custom_describe
    try:
        if action_name in action_custom_describe and all(map(is_simple, args)):
            return action_custom_describe[action_name](args)
        else:
            action_path = eval(f"actions.{action_name}")
            doc_string = repr(action_path)
            doc_string = doc_string.splitlines()[1]
            doc_string = doc_string.strip()
            if doc_string.startswith(("Return", "return", "Get", "get")):
                return " ".join(doc_string.split(" ")[1:])
            else:
                return [doc_string]
    except Exception as e:
        if isinstance(e, IndexError):
            print(f"Action {action_name} has no documentation.")
        else:
            print(f"Could not describe {action_name} with arguments {args}: {e}")
        return None


def describe_expr(expr: Expr) -> DocString:
    """Describe what the TalonScript expression does

    Parameters:
    expr (Expr):
        A TalonScript expression.

    Returns:
    Union[str, list[str]]:
        A string which describes the behavior of the expression.
        If the returned value is a single string, it can be combined horizontally with other doc strings.
        Otherwise, it can only be combined vertically.
    """
    # Describe operator expressions:
    if isinstance(expr, ExprOp):
        v1 = describe_expr(expr.v1)
        v2 = describe_expr(expr.v2)
        # Special cases for default values:
        if isinstance(expr, ExprOr):
            if (
                isinstance(expr.v1, Variable)
                and isinstance(expr.v2, StringValue)
                and expr.v2.value == ""
            ):
                return f"<{expr.v1.name} or ''>"
            if (
                isinstance(expr.v2, Variable)
                and isinstance(expr.v1, StringValue)
                and expr.v1.value == ""
            ):
                return f'<{expr.v2.name} or "">'
            if is_simple(v1) and isinstance(v2, list):
                return [*v2, f"Using a default value of {v1}."]
            if isinstance(v2, list) and is_simple(v2):
                return [*v1, f"Using a default value of {v2}."]
        # Combine both horizontally:
        if is_simple(v1) and is_simple(v2):
            return f"{v1} {expr.op} {v2}"
        # Refuse to combine both vertically:
        else:
            print(f"Cowardly refusing to compose complex operation {expr}")
            return None

    # Describe values:
    if isinstance(expr, Value):
        # Literals describe themselves:
        if isinstance(expr, (StringValue, NumberValue)):
            if expr.value:
                return str(expr.value).replace("\n", "\\n")
            else:
                return "''"

        # Format strings may be composed horizontally if all their parts are primitives:
        elif isinstance(expr, FormatStringValue):
            parts = map(describe_expr, expr.parts)
            if all(map(is_simple, parts)):
                return "".join(parts)
            # Refuse to combine parts vertically:
            else:
                print(
                    f"Cowardly refusing to compose parts of complex format string {expr}"
                )
                return None
        # Otherwise, we may simply risk it:
        else:
            return str(expr.value)

    # Describe variables:
    if isinstance(expr, Variable):
        return f"<{expr.name}>"

    # Describe actions:
    if isinstance(expr, Action):
        args = tuple(describe_expr(arg) for arg in expr.args)
        return describe_action(expr.name, args)

    # Describe key statements via the key action:
    if isinstance(expr, KeyStatement):
        return describe_action("key", ("-".join(map(describe_expr, expr.keys)),))

    # Described repeat:
    if isinstance(expr, Repeat):
        value = describe_expr(expr.value)
        if is_simple(value):
            return [f"Repeat {value} times"]
        else:
            print(f"Cowardly refusing to compose complex repeat {expr}")
            return None

    # Describe variable assignment:
    if isinstance(expr, Assignment):
        rhs = describe_expr(expr.expr)
        if is_simple(rhs):
            return [f"Let <{expr.var}> be {rhs}"]
        else:
            print(
                f"Cowardly refusing to document complex variable assignment {expr} with right hand side {rhs}"
            )
            return None

    # Other statements (Comment, Sleep) are ignored:
    else:
        return []


def describe_command(command: CommandImpl) -> Optional[list[str]]:
    """Create documentation for command based on documentation of the components of its TalonScript"""
    docs: MutableSequence[str] = []
    for lines in map(describe_expr, command.target.lines):
        if isinstance(lines, str):
            docs.append(lines)
        elif isinstance(lines, list):
            docs += lines
        else:
            return None
    return docs


def describe_command_implementation(command: CommandImpl) -> str:
    """Created documentation for command based on its TalonScript"""
    return "\n".join(map(str.strip, command.target.code.splitlines()))


def describe_context_name(context_name: str) -> Optional[str]:
    GuessContextOS = re.compile(r".*(mac|win|linux).*")
    os = GuessContextOS.search(context_name)
    os = f" ({os.group(1)})" if os else ""
    GuessContextName = re.compile(r".*\.([^\.]+)(\.(mac|win|linux))?\.talon")
    short_name = GuessContextName.search(context_name)
    if short_name:
        short_name = short_name.group(1).capitalize()
    else:
        print(f"Describe context name failed for {context_name}")
        return context_name
    return short_name + os


# Instance which prints an HTML document to a file
class HtmlCell(Cell):
    def __init__(self, row, verbatim: bool = False):
        self.row = row
        self.first_line = True
        self.verbatim = verbatim

    def __enter__(self):
        self.row.table.doc.file.write(f"<td>\n")
        if self.verbatim:
            self.row.table.doc.file.write(f"<pre>\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if self.verbatim:
            self.row.table.doc.file.write(f"</pre>\n")
        self.row.table.doc.file.write(f"</td>\n")

    def line(self, contents: str):
        if self.first_line:
            self.first_line = False
        else:
            self.row.table.doc.file.write("<br />\n")
        self.row.table.doc.file.write(HtmlDoc.escape(contents) + "\n")


class HtmlRow(Row):
    def __init__(self, table):
        self.table = table

    def __enter__(self):
        self.table.doc.file.write(f"<tr>\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.table.doc.file.write(f"</tr>\n")

    def cell(self, contents: Optional[str] = None, verbatim: bool = False):
        cell = HtmlCell(self)
        if contents:
            with cell:
                cell.line(contents)
        else:
            return cell


class HtmlTable(Table):
    def __init__(self, doc):
        self.doc = doc
        self.body = False

    def __enter__(self):
        self.doc.file.write(f"<table>\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.doc.file.write(f"</tbody>\n")
        self.doc.file.write(f"</table>\n")

    def title(self, title: str):
        if not self.body:
            self.doc.file.write(f"<thead>\n")
            self.doc.file.write(f"<tr>\n")
            self.doc.file.write(f"<th>{HtmlDoc.escape(title)}</th>\n")
            self.doc.file.write(f"</th>\n")
            self.doc.file.write(f"</tr>\n")
            self.doc.file.write(f"</thead>\n")
        else:
            print("Title ignored in table body")

    def row(self):
        if not self.body:
            self.doc.file.write(f"<tbody>\n")
            self.body = True
        return HtmlRow(self)


class HtmlDoc(Doc):
    @staticmethod
    def escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def __init__(self, html_file_path: str, css_file_path: Optional[str]=None):
        self.css_file_path = css_file_path
        self.file = open(html_file_path, "w")
        self.body = False

    def __enter__(self):
        self.file.write("<!doctype html>\n")
        self.file.write('<html lang="en">\n')
        self.file.write("<head>\n")
        self.file.write('<meta charset="utf-8">\n')
        if self.css_file_path and os.path.exists(self.css_file_path):
            self.file.write('<style type="text/css">\n')
            with open(self.css_file_path, 'r') as css:
                self.file.write(f"{css.read().rstrip()}\n")
            self.file.write('</style>\n')
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.write(f"</body>\n")
        self.file.write(f"</html>\n")
        self.file.close()

    def title(self, title: str):
        if not self.body:
            self.file.write(f"<title>{HtmlDoc.escape(title)}</title>\n")
        else:
            print("Title ignored in table body")

    def table(self):
        if not self.body:
            self.file.write("</head>\n")
            self.file.write("<body>\n")
            self.body = True
        return HtmlTable(self)


@mod.action_class
class CheatSheetActions:
    def cheatsheet():
        """Print out a sheet of Talon commands."""
        this_dir = os.path.dirname(os.path.realpath(__file__))
        html_file_path = os.path.join(this_dir, "cheatsheet.html")
        css_file_path = os.path.join(this_dir, "cheatsheet.css")
        with HtmlDoc(html_file_path, css_file_path) as doc:
            doc.title("Talon Cheatsheet")
            doc.list("user.letter")
            doc.list("user.number_key")
            doc.list("user.modifier_key")
            doc.list("user.special_key")
            doc.list("user.symbol_key")
            doc.list("user.arrow_key")
            doc.list("user.punctuation")
            doc.list("user.function_key")
            doc.formatters()
            for context_name, context in registry.contexts.items():
                doc.context(context_name, context)
