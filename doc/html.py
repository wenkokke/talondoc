from __future__ import annotations
from typing import *
from user.cheatsheet.doc.abc import *
import os

# Instance which prints an HTML document to a file


class HtmlRow(Row):
    def __init__(self, table):
        self.tab = table

    def __enter__(self) -> HtmlRow:
        self.tab.sec.doc.file.write(f"<tr>\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.tab.sec.doc.file.write(f"</tr>\n")

    def cell(self, contents: str, verbatim: bool = False):
        self.tab.sec.doc.file.write(f"<td>\n")
        if verbatim:
            self.tab.sec.doc.file.write(f"<pre>\n")
            self.tab.sec.doc.file.write(f"{contents}")
            self.tab.sec.doc.file.write(f"</pre>\n")
        else:
            for line in contents.splitlines():
                line = HtmlDoc.escape(line).replace("\n","<br />\n")
                self.tab.sec.doc.file.write(f"{line}\n")
        self.tab.sec.doc.file.write(f"</td>\n")


class HtmlTable(Table):
    def __init__(self, sec, title: str, cols: int, anchor: Optional[str] = None):
        self.sec = sec
        self.title = title
        self.cols = cols
        self.css_class = anchor

    def __enter__(self) -> HtmlTable:
        if self.css_class:
            self.sec.doc.file.write(f'<div class="{self.css_class}">\n')
        else:
            self.sec.doc.file.write(f"<div>\n")
        self.sec.doc.file.write(f"<table>\n")
        self.sec.doc.file.write(f"<thead>\n")
        self.sec.doc.file.write(f"<tr>\n")
        self.sec.doc.file.write(
            f'<th colspan="{self.cols}">{HtmlDoc.escape(self.title)}</th>\n'
        )
        self.sec.doc.file.write(f"</tr>\n")
        self.sec.doc.file.write(f"</thead>\n")
        self.sec.doc.file.write(f"<tbody>\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.sec.doc.file.write(f"</tbody>\n")
        self.sec.doc.file.write(f"</table>\n")
        self.sec.doc.file.write(f"</div>\n")

    def row(self) -> HtmlRow:
        return HtmlRow(self)


class HtmlSection(Section):
    def __init__(self, doc, title: str, cols: int = 1, anchor: Optional[str] = None):
        self.doc = doc
        self.title = title
        self.cols = cols
        self.css_class = anchor or ""

    def __enter__(self) -> HtmlSection:
        self.doc.file.write(f"<h1>{HtmlDoc.escape(self.title)}</h1>\n")
        self.doc.file.write(
            f'<section class="section-{self.cols}-cols {self.css_class}">\n'
        )
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.doc.file.write(f"</section>\n")

    def table(self, title: str, cols: int = 1, anchor: Optional[str] = None) -> HtmlTable:
        return HtmlTable(self, title, cols, anchor)


class HtmlDoc(Doc):
    @staticmethod
    def escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def __init__(
        self, title: str, html_file_path: str, css_file_path: Optional[str] = None
    ):
        self.css_file_path = css_file_path
        self.file = open(html_file_path, "w")
        self.title = title

    def __enter__(self) -> HtmlDoc:
        self.file.write(f"<!doctype html>\n")
        self.file.write(f'<html lang="en">\n')
        self.file.write(f"<head>\n")
        self.file.write(f'<meta charset="utf-8">\n')
        self.file.write(f"<title>{HtmlDoc.escape(self.title)}</title>\n")
        if self.css_file_path and os.path.exists(self.css_file_path):
            with open(self.css_file_path, "r") as f:
                self.file.write(f'<style type="text/css">\n')
                self.file.write(f"{f.read().strip()}\n")
                self.file.write(f"</style>\n")
        self.file.write(f"</head>\n")
        self.file.write(f"<body>\n")
        self.file.write(f"<main>\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.write(f"</main>\n")
        self.file.write(f"</body>\n")
        self.file.write(f"</html>\n")
        self.file.close()

    def section(self, title: str, cols: int = 1, anchor: Optional[str] = None) -> HtmlSection:
        return HtmlSection(self, title, cols, anchor)
