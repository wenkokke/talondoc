from typing import *
from user.cheatsheet.doc.abc import *
import os

# Instance which prints an HTML document to a file
class HtmlCell(Cell):
    def __init__(self, row, verbatim: bool = False):
        self.row = row
        self.first_line = True
        self.verbatim = verbatim

    def __enter__(self):
        self.row.tab.sec.doc.file.write(f"<td>\n")
        if self.verbatim:
            self.row.tab.sec.doc.file.write(f"<pre>\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if self.verbatim:
            self.row.tab.sec.doc.file.write(f"</pre>\n")
        self.row.tab.sec.doc.file.write(f"</td>\n")

    def line(self, contents: str):
        if self.first_line:
            self.first_line = False
        else:
            self.row.tab.sec.doc.file.write(f"<br />\n")
        self.row.tab.sec.doc.file.write(f"{HtmlDoc.escape(contents)}\n")


class HtmlRow(Row):
    def __init__(self, table):
        self.tab = table

    def __enter__(self):
        self.tab.sec.doc.file.write(f"<tr>\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.tab.sec.doc.file.write(f"</tr>\n")

    def cell(self, contents: Optional[str] = None, verbatim: bool = False):
        cell = HtmlCell(self)
        if contents:
            with cell:
                cell.line(contents)
        else:
            return cell


class HtmlTable(Table):
    def __init__(self, sec, title: str, cols: int, anchor: Optional[str] = None):
        self.sec = sec
        self.title = title
        self.cols = cols
        self.css_class = anchor

    def __enter__(self):
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
        self.sec.doc.file.write(f"</th>\n")
        self.sec.doc.file.write(f"</tr>\n")
        self.sec.doc.file.write(f"</thead>\n")
        self.sec.doc.file.write(f"<tbody>\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.sec.doc.file.write(f"</tbody>\n")
        self.sec.doc.file.write(f"</table>\n")
        self.sec.doc.file.write(f"</div>\n")

    def row(self):
        return HtmlRow(self)


class HtmlSection(Section):
    def __init__(self, doc, title: str, cols: int, anchor: Optional[str] = None):
        self.doc = doc
        self.title = title
        self.cols = cols
        self.css_class = anchor or ""

    def __enter__(self):
        self.doc.file.write(f"<h1>{HtmlDoc.escape(self.title)}</h1>\n")
        self.doc.file.write(
            f'<section class="section-{self.cols}-cols {self.css_class}">\n'
        )
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.doc.file.write(f"</section>\n")

    def table(self, title: str, cols: int, anchor: Optional[str] = None):
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

    def __enter__(self):
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

    def section(self, title: str, cols: int, anchor: Optional[str] = None):
        return HtmlSection(self, title, cols, anchor)
