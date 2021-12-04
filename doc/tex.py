from typing import *
from user.cheatsheet.doc.abc import *
import os

# Instance which prints an HTML document to a file
class TeXCell(Cell):
    def __init__(self, row, verbatim: bool = False):
        self.row = row
        self.verbatim = verbatim
        self.first_line = True

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        pass

    def line(self, contents: str):
        if self.first_line:
            self.first_line = False
        else:
            self.row.tab.sec.doc.file.write(f"\\newline%\n")
        if self.verbatim:
            c = TeXDoc.verbatim_character(contents)
            for line in contents.splitlines():
                self.row.tab.sec.doc.file.write(f"\\verb{c}{line}{c}%\n")
        else:
            self.row.tab.sec.doc.file.write(TeXDoc.escape(contents) + "%\n")


class TeXRow(Row):
    def __init__(self, table):
        self.first_cell = True
        self.tab = table

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.tab.sec.doc.file.write(f"\\\\ \\hline%\n")

    def cell(self, contents: Optional[str] = None, verbatim: bool = False):
        if self.first_cell:
            self.first_cell = False
        else:
            self.tab.sec.doc.file.write(f"&%\n")
        cell = TeXCell(self, verbatim=verbatim)
        if contents:
            with cell:
                cell.line(contents)
        else:
            return cell


class TeXTable(Table):
    def __init__(self, sec, title: str, cols: int, anchor: Optional[str] = None):
        self.sec = sec
        self.title = title
        self.cols = cols

    def __enter__(self):
        self.sec.doc.file.write(f"\\setbox\\ltmcbox\\vbox{{%\n")
        self.sec.doc.file.write(f"\\makeatletter\\col@number\\@ne%\n")
        textwidth_ratio = 1.0 / self.cols
        tabcolsep_ratio = 1.0 + 1.0 / (self.cols - 2) if self.cols > 2 else 1.0
        table_format = (
            f"@{{}}p{{\\dimexpr {textwidth_ratio}\\linewidth - {tabcolsep_ratio}\\tabcolsep \\relax}}"
            * self.cols
        ) + "@{{}}"
        self.sec.doc.file.write(f"\\begin{{longtable}}{{{table_format}}}%\n")
        self.sec.doc.file.write(
            f"\\caption{{\\bf {TeXDoc.escape(self.title)}}} \\\\ \\hline%\n"
        )
        self.sec.doc.file.write(f"\\endfirsthead%\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.sec.doc.file.write(f"\\end{{longtable}}%\n")
        self.sec.doc.file.write(f"\\unskip%\n")
        self.sec.doc.file.write(f"\\unpenalty%\n")
        self.sec.doc.file.write(f"\\unpenalty}}%\n")
        self.sec.doc.file.write(f"\\unvbox\\ltmcbox%\n")

    def row(self):
        return TeXRow(self)


class TeXSection(Section):
    def __init__(self, doc, title: str, cols: int, anchor: Optional[str] = None):
        self.doc = doc
        self.title = title
        self.cols = cols

    def __enter__(self):
        if self.cols > 1:
            self.doc.file.write(f"\\begin{{multicols}}{{{self.cols}}}%\n")
        self.doc.file.write(f"\\section{{{self.title}}}%\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if self.cols > 1:
            self.doc.file.write(f"\\end{{multicols}}%\n")
        self.doc.file.write(f"\\clearpage%\n")

    def table(self, title: str, cols: int, anchor: Optional[str] = None):
        return TeXTable(self, title, cols, anchor)


class TeXDoc(Doc):
    @staticmethod
    def escape(text: str) -> str:
        return (
            text.replace("\\", "\\textbackslash ")
            .replace("&", "\\&\\xspace ")
            .replace("%", "\\%")
            .replace("$", "\\$")
            .replace("#", "\\#")
            .replace("_", "\\_")
            .replace("{", " \\{ ")
            .replace("}", " \\}\\xspace ")
            .replace("[", "{[}")
            .replace("]", "{]}\\xspace ")
            .replace('"', "\\textquotedbl ")
            .replace("'", "\\textquotesingle ")
            .replace("|", " \\textbar\\xspace ")
            .replace("<", " \\textless ")
            .replace(">", "\\textgreater\\xspace ")
            .replace("~", "\\textasciitilde ")
            .replace("^", "\\textasciicircum ")
        )

    @staticmethod
    def verbatim_character(text: str) -> str:
        return next(filter(lambda c: not c in text, "|\"'=+-!"))

    def __init__(
        self,
        title: str,
        tex_file_path: str,
        tex_preamble_file_path: Optional[str] = None,
        document_class: str = "article",
        document_options: str = "",
    ):
        self.title = title
        self.file = None
        self.tex_file_path = tex_file_path
        self.tex_preamble_file_path = tex_preamble_file_path
        self.doc_class = document_class
        self.doc_options = document_options

    def __enter__(self):
        self.file = open(self.tex_file_path, 'w')
        self.file.write(f"\\documentclass[{self.doc_options}]{{{self.doc_class}}}%\n")
        if self.tex_preamble_file_path and os.path.exists(self.tex_preamble_file_path):
          with open(self.tex_preamble_file_path, 'r') as f:
            self.file.write(f"{f.read().strip()}\n")
        self.file.write(f"\\begin{{document}}%\n")
        self.file.write(f"{{\\Huge\\bf {TeXDoc.escape(self.title)}}}%\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.write(f"\\clearpage%\n")
        self.file.write(f"\\thispagestyle{{empty}}%\n")
        self.file.write(f"\\listoftables%\n")
        self.file.write(f"\\end{{document}}\n")
        self.file.close()

    def section(self, title: str, cols: int, anchor: Optional[str] = None):
        return TeXSection(self, title, cols, anchor)


