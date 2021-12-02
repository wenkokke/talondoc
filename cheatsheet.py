from contextlib import nullcontext
from talon import  Module, actions, registry
from talon.scripting.context import Context
from talon.scripting.talon_script import *
from talon.scripting.types import CommandImpl
from io import TextIOWrapper
from typing import *

import os
import re
import sys

mod = Module()


def write_talon_list(file: TextIOWrapper, list_name:str) -> None:
    """Write a Talon list as an HTML table"""
    file.write(f"<table class=\"talon-list\">\n")
    file.write(f"<thead>\n")
    file.write(f"\t<tr>\n")
    file.write(f"\t\t<th colspan=\"2\">{list_name}</tr>\n")
    file.write(f"\t</th>\n")
    file.write(f"\t</tr>\n")
    file.write(f"</thead>\n")
    file.write(f"<tbody>\n")
    command_list = registry.lists[list_name][0].items()
    for key, value in command_list:
        file.write(f"\t<tr>\n")
        file.write(f"\t\t<td class=\"talon-list-key\">{key}</td>\n")
        file.write(f"\t\t<td class=\"talon-list-value\">{value}</td>\n")
        file.write(f"\t</tr>\n")
    file.write(f"</tbody>\n")
    file.write(f"</table>\n\n")


def write_formatters(file: TextIOWrapper) -> None:
    """Write a formatter as a markdown table with an example"""
    file.write(f"<table class=\"talon-formatters\">\n")
    file.write(f"<thead>\n")
    file.write(f"\t<tr>\n")
    file.write(f"\t\t<th colspan=\"2\">Formatters</tr>\n")
    file.write(f"\t</th>\n")
    file.write(f"\t</tr>\n")
    file.write(f"</thead>\n")
    file.write(f"<tbody>\n")
    command_list = registry.lists['user.formatters'][0].items()
    for key, _ in command_list:
        file.write(f"\t<tr>\n")
        example = actions.user.formatted_text(f"example of formatting with {key}", key)
        file.write(f"\t<td class=\"talon-formatter-key\">{key}</td>\n")
        file.write(f"\t<td class=\"talon-formatter-example\">{example}</td>\n")
        file.write(f"\t</tr>\n")
    file.write(f"</tbody>\n")
    file.write(f"</table>\n\n")


def describe_context_name(context_name: str) -> str:
    """
    The logic here is intended to only print from talon files that have actual voice commands.
    """
    splits = context_name.split(".")
    index = -1

    if "mac" in context_name:
        os = "mac"
    elif "win" in context_name:
        os = "win"
    elif "linux" in context_name:
        os = "linux"
    else:
        os = ""

    if "talon" in splits[index]:
        index = -2
        short_name = splits[index].replace("_", " ")
    else:
        short_name = splits[index].replace("_", " ")

    if short_name in ["mac", "win", "linux"]:
        index = index - 1
        short_name = splits[index].replace("_", " ")

    return f"{os} {short_name}".strip()


def write_context(file: TextIOWrapper, context_name:str, context: Context) -> None:
    """Write each command and its implementation"""
    if context.commands:
        file.write(f"<table class=\"talon-context\">\n")
        file.write(f"<thead>\n")
        file.write(f"\t<tr>\n")
        file.write(f"\t\t<th colspan=\"2\">{describe_context_name(context_name)}</tr>\n")
        file.write(f"\t</th>\n")
        file.write(f"\t</tr>\n")
        file.write(f"</thead>\n")
        file.write(f"<tbody>\n")
        for command in context.commands.values():
            rule = command.rule.rule
            docs = describe_command(command)
            impl = describe_command_implementation(command)
            if docs:
                file.write(f"\t<tr>\n")
                file.write(f"\t\t<td rowspan=\"2\" class=\"talon-command-rule\">{rule}</td>\n")
                file.write(f"\t\t<td class=\"talon-command-docs\">\n")
                for line in docs:
                    file.write(f"\t\t\t{line.strip()}<br />\n")
                file.write(f"\t\t</td>\n")
                file.write(f"\t<tr>\n")
                file.write(f"\t\t<td class=\"talon-command-impl\">\n")
                file.write(f"<pre>{impl}</pre>\n")
                file.write(f"</td>\n")
                file.write(f"\t<tr>\n")
            else:
                file.write(f"\t<tr>\n")
                file.write(f"\t\t<td class=\"talon-command-rule\">{rule}</td>\n")
                file.write(f"\t\t<td class=\"talon-command-impl\"><pre>\n")
                file.write(f"\t\t\t{impl}\n")
                file.write(f"\t\t</pre></td>\n")
                file.write(f"\t<tr>\n")
        file.write(f"</tbody>\n")
        file.write(f"</table>\n\n")
    else:
        print(f"{context_name}: Defines no commands")


"""The type of documentation strings:
If the value is None, there is no documentation.
If the value is a string, it represents documentation which can be composed horizontally.
Otherwise, if the value is a list of strings, it represents documentation which can be composed vertically."""
Doc = Union[None, str, list[str]]


def is_simple(doc: Doc) -> bool:
    """Check whether a document string can be composed horizontally"""
    return type(doc) == str


def describe_action_custom(action_name: str, args: list[Doc]) -> Doc:
    """Return the custom formatting string for the action, if available"""
    if all(map(is_simple, args)):
        try:
            return {
                'key'                : ["Press {}".format(*args)],
                'insert'             : ["Insert <code>{}</code>".format(*args)],
                'auto_insert'        : ["Insert <code>{}</code> using automatic formatting".format(*args)],
                'sleep'              : [],
                'edit.selected_text' : "the selected text",
                'user.vscode'        : ["Execute {}".format(*args)],
            }.get(action_name)
        except (KeyError, IndexError):
            pass
    return None


def describe_action(action_name: str) -> Doc:
    """Return the doc string for the action, if available"""
    if action_name in ['sleep']:
        return []
    else:
        try:
            action_path = eval(f"actions.{action_name}")
            doc_string = repr(action_path)
            doc_string = doc_string.splitlines()[1]
            doc_string = doc_string.strip()
            if doc_string.startswith(('Return', 'return')):
                return ' '.join(doc_string.split(' ')[1:])
            else:
                return [doc_string]
        except Exception as e:
            if isinstance(e, IndexError):
                print(f"Action {action_name} has no documentation.")
            else:
                print(f"Could not describe {action_name}: {e}")
            return None


def describe(expr: Expr) -> Doc:
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
        v1 = describe(expr.v1)
        v2 = describe(expr.v2)
        # Special cases for default values:
        if isinstance(expr, ExprOr):
            if isinstance(expr.v1, Variable) and isinstance(expr.v2, StringValue) and expr.v2.value == "":
                return f"&lt;{expr.v1.name} or \"\"&gt;"
            if isinstance(expr.v2, Variable) and isinstance(expr.v1, StringValue) and expr.v1.value == "":
                return f"&lt;{expr.v2.name} or \"\"&gt;"
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
                return str(expr.value).replace("\n","\\n")
            else:
                return "an empty string"

        # Format strings may be composed horizontally if all their parts are primitives:
        elif isinstance(expr, FormatStringValue):
            parts = map(describe, expr.parts)
            if all(map(is_simple, parts)):
                return "".join(parts)
            # Refuse to combine parts vertically:
            else:
                print(f"Cowardly refusing to compose parts of complex format string {expr}")
                return None
        # Otherwise, we may simply risk it:
        else:
            return str(expr.value)

    # Describe variables:
    if isinstance(expr, Variable):
        return f"&lt;{expr.name}&gt;"

    # Describe actions:
    if isinstance(expr, Action):
        args = list(map(describe, expr.args))
        custom_doc = describe_action_custom(expr.name, args)
        doc_string = describe_action(expr.name)
        return custom_doc or doc_string

    # Describe key statements via the key action:
    if isinstance(expr, KeyStatement):
        return describe_action_custom('key', "-".join(map(describe, expr.keys)))

    # Described repeat:
    if isinstance(expr, Repeat):
        value = describe(expr.value)
        if is_simple(value):
            return [f"Repeat {value} times"]
        else:
            print(f"Cowardly refusing to compose complex repeat {expr}")
            return None

    # Describe variable assignment:
    if isinstance(expr, Assignment):
        rhs = describe(expr.expr)
        if is_simple(rhs):
            return [f"Let &lt;{expr.var}&gt; be {rhs}"]
        else:
            print(f"Cowardly refusing to document complex variable assignment {expr} with right hand side {rhs}")
            return None

    # Other statements (Comment, Sleep) are ignored:
    else:
        return []


def describe_command(command: CommandImpl) -> Optional[list[str]]:
    """Create documentation for command based on documentation of the components of its TalonScript"""
    docs: MutableSequence[str] = []
    for lines in map(describe, command.target.lines):
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

@mod.action_class
class CheatSheetActions:

    def cheatsheet():
        """Print out a sheet of Talon commands."""

        this_dir = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(this_dir, 'cheatsheet.html')
        with open(file_path, 'w') as file:

            file.write("<!doctype html>\n")
            file.write("<html lang=\"en\">\n")
            file.write("<head>\n")
            file.write("<meta charset=\"utf-8\">\n")
            file.write("<link href=\"cheatsheet.css\" rel=\"stylesheet\">\n")
            file.write("<title>Talon Cheatsheet</title>\n")
            file.write("</head>\n")
            file.write("<body>\n")
            write_talon_list(file, 'user.letter')
            write_talon_list(file, 'user.number_key')
            write_talon_list(file, 'user.modifier_key')
            write_talon_list(file, 'user.special_key')
            write_talon_list(file, 'user.symbol_key')
            write_talon_list(file, 'user.arrow_key')
            write_talon_list(file, 'user.punctuation')
            write_talon_list(file, 'user.function_key')
            write_formatters(file)
            for context_name, context in registry.contexts.items():
                write_context(file, context_name, context)
            file.write("</body>\n")
            file.write("</html>\n")