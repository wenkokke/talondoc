from docstring_parser.google import ParseError, parse
from talon import actions  # type: ingore
from talon.scripting.context import *  # type: ignore
from talon.scripting.talon_script import *  # type: ignore
from talon.scripting.types import *  # type: ignore
from typing import *
from user.cheatsheet.doc.talon_script.description import *
from user.cheatsheet.doc.talon_script.walker import TalonScriptWalker

import re


class Describe(TalonScriptWalker):

    # Describing contexts and commands

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

    @staticmethod
    def command(command: CommandImpl) -> Optional[str]:
        """Describe a Talon context"""
        try:
            desc_lines = Describe().fold_command(command)
            desc = flatten(desc_lines)
            desc = desc.compile()
            return desc
        except MissingDocumentation as e:
            print(f"Action '{e.action_name}' has no documentation")
            return None
        except InvalidInterpolation as e:
            print(f"Could not interpolate multiline documentation:")
            for line in e.lines:
                print(f"\t{line}")

    # Describing actions

    def action(self, name: str, args: Sequence[Expr]) -> Description:
        """Describe an action.

        The following methods are tried in order:
        1. using a custom description function;
        2. describing an action which returns a value as a chunk, based on textual heuristics;
        3. describing an action using its docstring, interpolating the descriptions of the parameters;
        4. describing in action using its docstring.
        """
        # print(f"actions({name}, {args})")
        args: Sequence[Description] = tuple(map(self.fold_expr, args))
        return (
            Describe.try_describe_action_custom(name, args)
            or Describe.try_describe_action_chunk(name)
            or Describe.try_describe_action_template(name, args)
            or Describe.describe_action_line(name)
        )

    @staticmethod
    def try_describe_action_custom(
        action_name: str, args: Sequence[Description]
    ) -> Optional[Description]:
        """Describe the action using a custom function."""
        try:
            return {
                "key": lambda key_values: Line(f"Press {flatten(key_values)}"),
                "insert": lambda args: Line(f'Insert "{args[0]}"'),
                "auto_insert": lambda args: Line(f'Insert "{args[0]}"'),
                "sleep": lambda _: Ignore(),
                "repeat": lambda args: Line(f"Repeat {args[0]} times"),
                "edit.selected_text": lambda _: Chunk("the selected text"),
                "user.vscode": lambda _: Ignore(),
                "user.idea": lambda _: Ignore(),
                "user.formatted_text": lambda args: Chunk(f"{args[0]} (formatted with {args[1]})"),
                "user.homophones_select": lambda args: Chunk(f"homophone #{args[0]}"),
            }[action_name](args)
        except KeyError:
            return None

    ImpliesReturnValue = ("Return", "return", "Get")

    @staticmethod
    def try_describe_action_chunk(action_name: str) -> Optional[Chunk]:
        """Describe an action which returns a value as a chunk, based on textual heuristics."""
        desc_short = Describe.short_description(action_name)
        if desc_short.startswith(Describe.ImpliesReturnValue):
            desc_short_words = desc_short.split()
            if len(desc_short_words) > 1:
                desc_short = " ".join(desc_short_words[1:])
                return Chunk(desc_short)
        return None

    @staticmethod
    def try_describe_action_template(
        action_name: str, args: Sequence[Description]
    ) -> Optional[Description]:
        """Describe the action documentation as a template, based on parsing the docstring."""
        try:
            action_path: ActionPath = eval(f"actions.{action_name}")
            docstring = parse(action_path.__doc__)
            if docstring.short_description:
                template = Template(
                    docstring.short_description,
                    tuple(param.arg_name for param in docstring.params),
                )
                return template(args)
            else:
                return None
        except (NotImplementedError, KeyError):
            # When issue 443 is fixed this should be enabled:
            # print(f"Could not retrieve documentation for {action_name}")
            return None
        except ParseError:
            print(f"Could not parse documentation for {action_name}")
            return None

    @staticmethod
    def describe_action_line(action_name: str) -> Lines:
        """Described the action by simply returning its short description."""
        desc_short = Describe.short_description(action_name)
        return Line(desc_short)

    @staticmethod
    def short_description(action_name: str) -> str:
        """Return the short description for the action. Workaround for issue #443."""
        action_path: ActionPath = eval(f"actions.{action_name}")
        desc = repr(action_path)
        desc_lines = desc.splitlines()
        if len(desc_lines) < 2:
            raise MissingDocumentation(action_name)
        desc = desc_lines[1].strip()
        return desc

    # Describing other expressions

    def comment(self, text) -> Description:
        # print(f"{text}")
        return Ignore()

    def operator(self, v1: Expr, op: str, v2: Expr) -> Description:
        # print(f"operator({v1} {op} {v2})")
        v1 = self.fold_expr(v1)
        v2 = self.fold_expr(v2)
        return Chunk(f"{v1} {op} {v2}")

    def format_string(self, value: str, parts: Sequence[Expr]) -> Description:
        # print(f"format_string({value})")
        return flatten(tuple(map(self.fold_expr, parts)))

    def value(self, value: Any) -> Description:
        # print(f"value({value})")
        return Chunk(str(value).replace("\n", "\\n"))

    def variable(self, name: str) -> Description:
        # print(f"variable({name})")
        return Chunk(f"<{name}>")

    def assignment(self, var: str, expr: Expr) -> Description:
        expr = self.fold_expr(expr)
        return Line(f"Let <{var}> be {expr}")
