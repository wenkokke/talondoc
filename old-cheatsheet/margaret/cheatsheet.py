from talon import Module, actions, registry
from typing import *
from .doc.html import HtmlDoc
from .doc.tex import TeXDoc

import os

mod = Module()


@mod.action_class
class CheatSheetActions:
    def print_cheatsheet(format: str):
        """
        Print out a help document of all Talon commands as <format>

        Args:
            format: The format for the help document. Must be 'HTML' or 'TeX'.
        """
        this_dir = os.path.dirname(os.path.realpath(__file__))
        talon_cheatsheet_dir = os.path.join(this_dir, "..", "..", "cheatsheet")
        talon_cheatsheet_build_dir = os.path.join(talon_cheatsheet_dir, "build")
        talon_cheatsheet_css_dir = os.path.join(talon_cheatsheet_dir, "assets", "css")
        talon_cheatsheet_tex_dir = os.path.join(talon_cheatsheet_dir, "assets", "tex")

        if format.lower() == "html":
            doc = HtmlDoc(
                file_path=os.path.join(talon_cheatsheet_build_dir, "cheatsheet.html"),
                title="Talon Cheatsheet",
                css_include_path=os.path.join(talon_cheatsheet_css_dir, "style.css"),
            )

        if format.lower() == "html-dev":
            doc = HtmlDoc(
                file_path=os.path.join(
                    talon_cheatsheet_build_dir, "cheatsheet-dev.html"
                ),
                title="Talon Cheatsheet",
                css_href=os.path.join("..", "assets", "sass", "style.sass"),
            )

        if format.lower() == "tex":
            doc = TeXDoc(
                file_path=os.path.join(talon_cheatsheet_build_dir, "cheatsheet.tex"),
                title="Talon Cheatsheet",
                preamble_path=os.path.join(talon_cheatsheet_tex_dir, "preamble.tex"),
            )

        with doc:
            with doc.section(cols=2, css_classes="talon-lists") as sec:
                sec.list(
                    list_name="user.key_symbol",
                )
            with doc.section(cols=2, css_classes="talon-formatters") as sec:
                sec.formatters(
                    list_names=(
                        "user.formatter_code",
                        "user.formatter_prose",
                        "user.formatter_word",
                    ),
                    formatted_text=actions.user.format_text,
                )
            with doc.section(cols=2, css_classes="talon-contexts") as sec:
                for context_name, context in registry.contexts.items():
                    if not "personal" in context_name:
                        sec.context(context, context_name=context_name)
