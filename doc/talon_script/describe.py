from __future__ import annotations
from abc import *
from dataclasses import dataclass
from os import stat
from typing import *
from talon import actions  # Used by eval
from talon.scripting.context import *
from talon.scripting.talon_script import *
from talon.scripting.types import *
from user.cheatsheet.doc.talon_script.foldable import FoldableTalonScript
import traceback

import re


@dataclass(frozen=True)
class MissingDocumentation(Exception):
    """Exception raised when a doc string cannot be built"""

    action_name: str


@dataclass(frozen=True)
class InvalidInterpolation(Exception):
    """Exception raised when attempting to interpolate a multiline doc string"""

    lines: tuple[str]


@dataclass(frozen=True)
class UnknownDocString(Exception):
    """Exception raised you subclass DocString but don't update the existing join code"""

    value: Any


class DocString(ABC):
    def compile(self) -> str:
        """Compiles the DocString to a string."""
        return str(self)

    @staticmethod
    def join_all(doc_strings: Sequence[DocString]) -> DocString:
        if not doc_strings:
            return Ignore()
        else:
            result = doc_strings[0]
            for doc_string in doc_strings[1:]:
                result = result.join(doc_string)
            return result


@dataclass(frozen=True)
class Chunk(DocString):
    chunk: str

    def __str__(self):
        return self.chunk

    def join(self, other: DocString) -> DocString:
        if isinstance(other, Chunk):
            return Chunk(f"{self.chunk} {other.chunk}")
        elif isinstance(other, Lines):
            if not other.lines:
                return self  # preserve Chunk'ness
            else:
                return Lines((self.chunk, *other.lines))
        else:
            raise UnknownDocString(self)


@dataclass(frozen=True)
class Lines(DocString):
    lines: tuple[str]

    def compile(self) -> str:
        return "\n".join(self.lines)

    def __str__(self):
        raise InvalidInterpolation(self.lines)

    def join(self, other: DocString) -> DocString:
        if isinstance(other, Lines):
            return Lines((*self.lines, *other.lines))
        elif isinstance(other, Chunk):
            if not self.lines:
                return other  # preserve Chunk'ness
            else:
                return Lines((*self.lines, other.chunk))
        else:
            raise UnknownDocString(self)


def Line(text: str) -> DocString:
    return Lines((text,))


def Ignore() -> DocString:
    return Lines(tuple())


class Describe(FoldableTalonScript):
    @staticmethod
    def command(command: CommandImpl) -> Optional[str]:
        """Describe a Talon context"""
        try:
            doc_string_lines = Describe().fold_command(command)
            doc_string = DocString.join_all(doc_string_lines)
            doc_string = doc_string.compile()
            return doc_string
        except MissingDocumentation as e:
            print(f"Action '{e.action_name}' has no documentation")
            return None
        except InvalidInterpolation as e:
            print(f"Cannot interpolate multiline documentation")
            for line in e.lines:
                print(f"\t{line}")

    @staticmethod
    def context_name(context_name: str) -> str:
        GuessContextOS = re.compile(r".*(mac|win|linux).*")
        os = GuessContextOS.search(context_name)
        if os:
            OSMapping = {"mac": "MacOS", "win": "Windows", "linux": "Linux"}
            os = f" ({OSMapping.get(os.group(1))})"
        else:
            os = ""
        GuessContextName = re.compile(r".*\.([^\.]+)(\.(mac|win|linux))?\.talon")
        short_name = GuessContextName.search(context_name)
        if short_name:
            short_name = " ".join(map(str.capitalize, short_name.group(1).split("_")))
        else:
            return context_name
        return short_name + os

    """If the doc string starts with a word that implies returning a value,
    such as "return" or "get", we remove that word and allow composing the
    doc string horizontally.

    This could probably done in a little bit more of a principled way if we
    inspected the type of the action path. However, that way we still wouldn't
    know whether or not to strip the first word.

    The best way to go forward with this is probably to ensure that all doc
    strings for actions which return values have a certain form."""

    WordsWhichImplyReturnValues: tuple[str] = (
        "Get",
        "Return",
    )

    """Some common actions have a custom description."""
    ActionsWithCustomDescription: Dict[str, Callable[[tuple[DocString]], DocString]] = {
        "key": lambda key_values: Line(f"Press {DocString.join_all(key_values)}"),
        "insert": lambda args: Line(f'"{args[0]}"'),
        "auto_insert": lambda args: Line(f'"{args[0]}"'),
        "sleep": lambda _: Ignore(),
        "repeat": lambda args: Line(f"Repeat {args[0]} times"),
        "edit.selected_text": lambda _: Chunk("the selected text"),
        "user.formatted_text": lambda args: Chunk(
            f"{args[0]} (formatted with {args[1]})"
        ),
        "user.homophones_select": lambda args: Chunk(f"homophone #{args[0]}"),
    }

    def comment(self, text) -> DocString:
        # print(f"{text}")
        return Ignore()

    def operator(self, v1: Expr, op: str, v2: Expr) -> DocString:
        # print(f"operator({v1} {op} {v2})")
        v1 = self.fold_expr(v1)
        v2 = self.fold_expr(v2)
        return Chunk(f"{v1} {op} {v2}")

    def format_string(self, value: str, parts: Sequence[Expr]) -> DocString:
        # print(f"format_string({value})")
        return DocString.join_all(tuple(map(self.fold_expr, parts)))

    def value(self, value: Any) -> DocString:
        # print(f"value({value})")
        return Chunk(str(value).replace("\n", "\\n"))

    def variable(self, name: str) -> DocString:
        # print(f"variable({name})")
        return Chunk(f"<{name}>")

    @staticmethod
    def action_get_doc_string(name: str) -> str:
        """Get documentation via the Talon API"""
        action_path: ActionPath = eval(f"actions.{name}")
        doc_string_lines = repr(action_path).splitlines()
        if len(doc_string_lines) < 2:
            raise MissingDocumentation(name)
        else:
            return doc_string_lines[1].strip().capitalize().rstrip(".")

    @staticmethod
    def action_with_return_value(doc_string: str) -> Optional[DocString]:
        if doc_string.startswith(Describe.WordsWhichImplyReturnValues):
            doc_string_words = doc_string.split()
            if len(doc_string_words) > 1:
                doc_string = " ".join(doc_string_words[1:])
                return Chunk(doc_string)
        return None

    def action(self, name: str, args: Sequence[Expr]) -> DocString:
        # print(f"actions({name}, {args})")
        args = tuple(map(self.fold_expr, args))
        if name in Describe.ActionsWithCustomDescription:
            return Describe.ActionsWithCustomDescription[name](args)
        else:
            doc_string = Describe.action_get_doc_string(name)
            doc_string = Describe.action_with_return_value(doc_string) or Line(
                doc_string
            )
            return doc_string

    def assignment(self, var: str, expr: Expr) -> DocString:
        expr = self.fold_expr(expr)
        return Line(f"Let <{var}> be {expr}")
