from __future__ import annotations
from io import TextIOWrapper
from typing import *
from collections.abc import Iterable
from user.cheatsheet.doc.abc import *
import os


def html_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "\n<br />\n")
    )


def attr_class(kwargs) -> str:
    css_classes = kwargs.get("css_classes", [])
    if isinstance(css_classes, str):
        css_classes = [css_classes]
    elif isinstance(css_classes, Iterable):
        css_classes = list(css_classes)
    if "cols" in kwargs:
        css_classes.append(f"columns-{kwargs['cols']}")
    if css_classes:
        css_classes = " ".join(css_classes)
        css_classes = f' class="{css_classes}"'
        return css_classes
    else:
        return ""


def attr_colspan(kwargs) -> str:
    if "cols" in kwargs:
        return f" colspan=\"{kwargs['cols']}\""
    else:
        return ""


class HtmlRow(Row):
    def __init__(self, file: TextIOWrapper, **kwargs):
        self.file = file
        self.kwargs = kwargs

    def __enter__(self) -> HtmlRow:
        self.file.write(f"<tr>\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.write(f"</tr>\n")

    def cell(self, contents: str, **kwargs):
        self.file.write(f"<td{attr_class(kwargs)}>{html_escape(contents)}</td>\n")


class HtmlTable(Table):
    def __init__(self, file: TextIOWrapper, **kwargs):
        self.file = file
        self.kwargs = kwargs

    def __enter__(self) -> HtmlTable:
        self.file.write(f"<div{attr_class(self.kwargs)}>\n")
        self.file.write(f"<table>\n")

        if "title" in self.kwargs:
            self.file.write(f"<thead>")
            self.file.write(f"<tr>")
            self.file.write(
                f"<th{attr_colspan(self.kwargs)}>{html_escape(self.kwargs['title'])}</th>"
            )
            self.file.write(f"</tr>")
            self.file.write(f"</thead>")

        self.file.write(f"<tbody>\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.write(f"</tbody>")
        self.file.write(f"</table>")
        self.file.write(f"</div>")

    def row(self, **kwargs) -> HtmlRow:
        return HtmlRow(self.file, **kwargs)


class HtmlSection(Section):
    def __init__(self, file: TextIOWrapper, **kwargs):
        self.file = file
        self.kwargs = kwargs

    def __enter__(self) -> HtmlSection:
        if "title" in self.kwargs:
            self.file.write(f"<h1>{html_escape(self.kwargs['title'])}</h1>\n")
        self.file.write(f"<section{attr_class(self.kwargs)}>\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.write(f"</section>\n")

    def table(self, **kwargs) -> HtmlTable:
        return HtmlTable(self.file, **kwargs)


class HtmlDoc(Doc):
    def __init__(self, file_path: str, **kwargs):
        self.file = open(file_path, "w")
        self.kwargs = kwargs

    def __enter__(self) -> HtmlDoc:
        self.file.write(f"<!doctype html>\n")
        self.file.write(f'<html lang="en">\n')
        self.file.write(f"<head>\n")
        self.file.write(f'<meta charset="utf-8">\n')

        # Use **title as the document title:
        if "title" in self.kwargs:
            self.file.write(f"<title>{html_escape(self.kwargs['title'])}</title>\n")

        # Use **css_href in a link attribute:
        if "css_href" in self.kwargs:
            self.file.write(
                f"<link rel=\"stylesheet\" href=\"{self.kwargs['css_href']}\" />\n"
            )

        # Use **css_include_path as style file, inlined:
        if "css_include_path" in self.kwargs and os.path.exists(
            self.kwargs["css_include_path"]
        ):
            with open(self.kwargs["css_include_path"], "r") as f:
                self.file.write(f'<style type="text/css">{f.read().strip()}</style>\n')

        self.file.write(f"</head>\n")
        self.file.write(f"<body>\n")
        self.file.write(f"<main>\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.write(f"</main>\n")
        self.file.write(f"</body>\n")
        self.file.write(f"</html>\n")
        self.file.close()

    def section(self, **kwargs) -> HtmlSection:
        return HtmlSection(self.file, **kwargs)
