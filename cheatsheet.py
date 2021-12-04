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
        """Print out a sheet of Talon commands."""
        this_dir = os.path.dirname(os.path.realpath(__file__))

        if format == "html":
            html_file_path = os.path.join(this_dir, "cheatsheet.html")
            css_file_path = os.path.join(this_dir, "style.css")
            doc = HtmlDoc(
                title="Talon Cheatsheet",
                html_file_path=html_file_path,
                css_file_path=css_file_path,
            )

        if format == "tex":
            tex_file_path = os.path.join(this_dir, "cheatsheet.tex")
            tex_preamble_file_path = os.path.join(this_dir, "preamble.tex")
            doc = TeXDoc(
                title="Talon Cheatsheet",
                tex_file_path=tex_file_path,
                tex_preamble_file_path=tex_preamble_file_path,
                document_options="notitlepage",
            )

        with doc:
            with doc.section("Talon Lists", 4) as sec:
                sec.list("user.letter")
                sec.list("user.number_key")
                sec.list("user.modifier_key")
                sec.list("user.special_key")
                sec.list("user.symbol_key")
                sec.list("user.arrow_key")
                sec.list("user.punctuation")
                sec.list("user.function_key")
            with doc.section("Talon Formatters", 1) as sec:
                sec.formatters()
            with doc.section("Talon Contexts", 2) as sec:
                for context_name, context in registry.contexts.items():
                    sec.context(context_name, context)
