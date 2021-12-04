from abc import *
from typing import *
from talon import actions  # Used by eval
from talon.scripting.context import *
from talon.scripting.talon_script import *
from talon.scripting.types import *
from user.cheatsheet.doc.talon_script.foldable import FoldableTalonScript
import traceback

import re


"""The type of documentation strings:
If the value is None, there is no documentation.
If the value is a string, it represents documentation which can be composed horizontally.
Otherwise, if the value is a list of strings, it represents documentation which can be composed vertically."""
DocString = Union[None, str, list[str]]


def is_simple(doc: DocString) -> bool:
    """Check whether a document string can be composed horizontally"""
    return type(doc) == str


def all_simple(docs: Sequence[DocString]) -> bool:
    """Check whether a list of document strings can all be composed horizontally"""
    return all(map(is_simple, docs))


def flatten(docs: list[DocString]) -> Optional[str]:
    result: MutableSequence[str] = []
    for doc in docs:
        if type(doc) == str:
            result.append(doc)
        elif type(doc) == list[str]:
            result.extend(doc)
        elif type(doc) == None:
            return None
    return "\n".join(result)


def describe_command(command: CommandImpl) -> Optional[str]:
    """Describe a Talon context"""
    return flatten(Describe().fold_command(command))


def describe_context_name(context_name: str) -> Optional[str]:
    GuessContextOS = re.compile(r".*(mac|win|linux).*")
    os = GuessContextOS.search(context_name)
    if os:
        os = {"mac": "MacOS", "win": "Windows", "linux": "Linux"}.get(os.group(1))
        os = f" ({os})"
    else:
        os = ""
    GuessContextName = re.compile(r".*\.([^\.]+)(\.(mac|win|linux))?\.talon")
    short_name = GuessContextName.search(context_name)
    if short_name:
        short_name = " ".join(map(str.capitalize, short_name.group(1).split("_")))
    else:
        print(f"Describe context name failed for {context_name}")
        return context_name
    return short_name + os


class Describe(FoldableTalonScript):

    """If the doc string starts with a word that implies returning a value,
    such as "return" or "get", we remove that word and allow composing the
    doc string horizontally.

    This could probably done in a little bit more of a principled way if we
    inspected the type of the action path. However, that way we still wouldn't
    know whether or not to strip the first word.

    The best way to go forward with this is probably to ensure that all doc
    strings for actions which return values have a certain form."""

    WordsWhichImplyReturnValues: tuple[str] = (
        "get",
        "return",
    )

    @staticmethod
    def has_return_value(doc_string: Optional[str]) -> bool:
        if doc_string is None:
            return False
        return doc_string.lower().startswith(Describe.WordsWhichImplyReturnValues)

    @staticmethod
    def remove_first_word(doc_string: str) -> str:
        try:
            return " ".join(doc_string.split(" ")[1:])
        except IndexError:
            return doc_string

    """Some common actions have a custom description."""
    ActionsWithCustomDescription: Dict[str, Callable[[tuple[DocString]], DocString]] = {
        "key": lambda args: "Press {}".format(*args),
        "Key": lambda args: "Press {}".format(*args),
        "insert": lambda args: ['"{}"'.format(*args)],
        "auto_insert": lambda args: ['"{}"'.format(*args)],
        "sleep": lambda _: [],
        "repeat": lambda args: ["Repeat {} times".format(*args)],
        "edit.selected_text": lambda _: "the selected text",
        "user.vscode": lambda args: ["{}".format(*args)],
        "user.idea": lambda args: ["{}".format(*args)],
        "user.formatted_text": lambda args: "{} (formatted with {})".format(*args),
        "user.homophones_select": lambda args: "homophone number {}".format(*args),
    }

    @staticmethod
    def has_custom_description(name: str) -> bool:
        return name in Describe.ActionsWithCustomDescription

    @staticmethod
    def get_custom_description(
        name: str,
    ) -> Optional[Callable[[tuple[DocString]], DocString]]:
        return Describe.ActionsWithCustomDescription[name]

    @staticmethod
    def get_doc_string(name: str) -> Optional[str]:
        action_path: ActionPath = eval(f"actions.{name}")
        doc_string = repr(action_path)
        doc_string_lines = doc_string.splitlines()
        if len(doc_string_lines) < 2:
            print(f"Action {name} does not have documentation.")
            return None
        else:
            return doc_string_lines[1].strip()

    def comment(self, text) -> DocString:
        return []

    def operator_or(self, v1: Expr, op: str, v2: Expr) -> DocString:
        if isinstance(v1, Variable) and isinstance(v2, StringValue) and v2.value == "":
            return f"<{v1.name} or ''>"
        if isinstance(v2, Variable) and isinstance(v1, StringValue) and v1.value == "":
            return f"<{v2.name} or ''>"
        return self.operator(v1, op, v2)

    def operator(self, v1: Expr, op: str, v2: Expr) -> DocString:
        v1 = self.fold_expr(v1)
        v2 = self.fold_expr(v2)
        if is_simple(v1) and is_simple(v2):
            return f"{v1} {op} {v2}"
        else:
            print(f"Cowardly refusing to compose {v1} {op} {v2}")
            return None

    def format_string(self, value: str, parts: Sequence[Expr]) -> DocString:
        parts = map(self.fold_expr, parts)
        if all_simple(parts):
            return "".join(parts)
        else:
            print(f"Cowardly refusing to compose {parts}")
            return None

    def value(self, value: Any) -> DocString:
        return str(value).replace("\n", "\\n")

    def variable(self, name: str) -> DocString:
        return f"<{name}>"

    def action(self, name: str, args: Sequence[Expr]) -> DocString:
        args = tuple(map(self.fold_expr, args))
        try:
            if Describe.has_custom_description(name) and all_simple(args):
                return Describe.get_custom_description(name)(args)
            else:
                doc_string = Describe.get_doc_string(name)
                if Describe.has_return_value(doc_string):
                    return Describe.remove_first_word(doc_string)
                else:
                    return [doc_string]
        except Exception as e:
            print(f"Could not describe {name}{args}: {e}\n{traceback.format_exc()}")
            return None

    def assignment(self, var: str, expr: Expr) -> DocString:
        expr = self.fold_expr(expr)
        if is_simple(expr):
            return [f"Let <{var}> be {expr}"]
        else:
            print(f"Cowardly refusing to compose {var} = {expr}")
            return None
