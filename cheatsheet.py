from talon import Module, registry
from typing import *
from user.cheatsheet.doc.html import HtmlDoc
from user.cheatsheet.doc.tex import TeXDoc

import os
import re
import sys

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

        if format.lower() == "html":
            file_path = os.path.join(this_dir, "cheatsheet.html")
            css_include_path = os.path.join(this_dir, "dist", "style.css")
            doc = HtmlDoc(
                file_path, title="Talon Cheatsheet", css_include_path=css_include_path
            )

        if format.lower() == "html-dev":
            file_path = os.path.join(this_dir, "cheatsheet-dev.html")
            css_href = "style.sass"
            doc = HtmlDoc(file_path, title="Talon Cheatsheet", css_href=css_href)

        if format.lower() == "tex":
            file_path = os.path.join(this_dir, "cheatsheet.tex")
            doc = TeXDoc(
                file_path,
                title="Talon Cheatsheet",
                preamble_path="preamble.tex",
            )

        with doc:
            with doc.section(cols=3, css_classes="talon-lists") as sec:
                sec.list("user.letter")
                sec.list("user.number_key")
                sec.list("user.modifier_key")
                sec.list("user.special_key")
                sec.list("user.symbol_key")
                sec.list("user.arrow_key")
                sec.list("user.punctuation")
                sec.list("user.function_key")
            with doc.section(cols=1, css_classes="talon-formatters") as sec:
                sec.formatters()
            with doc.section(cols=2, css_classes="talon-contexts") as sec:
                for context_name, context in registry.contexts.items():
                    if not "personal" in context_name:
                        sec.context(context, context_name=context_name)
