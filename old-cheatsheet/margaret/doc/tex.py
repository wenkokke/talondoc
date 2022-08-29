from io import TextIOWrapper
from typing import *
from user.cheatsheet.doc.abc import *

import re

def tex_escape(text: str) -> str:
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    text = re.sub(r"\\(?![{}])", "{\\\\textbackslash}", text)
    text = text.replace("&", "\\&")
    text = text.replace("%", "\\%")
    text = text.replace("$", "\\$")
    text = text.replace("#", "\\#")
    text = text.replace("_", "\\_{\\allowbreak}")
    text = text.replace("[", "{[}")
    text = text.replace("]", "{]}")
    text = text.replace('"', "{\\textquotedbl}")
    text = text.replace("'", "{\\textquotesingle}")
    text = text.replace("|", "{\\textbar}")
    text = text.replace("<", "{\\textlangle}")
    text = text.replace(">", "{\\textrangle}")
    text = text.replace("~", "{\\textasciitilde}")
    text = text.replace("^", "{\\textasciicircum}")
    text = text.replace("£", "{\\textsterling}")
    text = text.replace("€", "{\\texteuro}")
    text = text.replace("–", "{\\textendash}")
    text = text.replace("—", "{\\textemdash}")
    text = text.replace(".", ".{\\allowbreak}")
    text = re.sub(r'\\n+', "\n\\\\newline%\n", text)
    return text

def tex_verbatim(text: str) -> str:
    char = tex_verbatim_character(text)
    return f"\\Verb{char}{text}{char}"


def tex_verbatim_character(text: str) -> str:
    return next(filter(lambda c: not c in text, "|\"'=+-!"))


class TeXRow(Row):
    def __init__(self, file: TextIOWrapper, **kwargs):
        self.first_cell = True
        self.file = file
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.write(f"\\\\%\n")

    def cell(self, contents: str, **kwargs):
        if self.first_cell:
            self.first_cell = False
        else:
            self.file.write(f"&%\n")
        if self.kwargs.get("verbatim", False):
            for line in contents.splitlines():
                self.file.write(f"{tex_verbatim(line)}\\newline%\n")
        else:
            contents = tex_escape(contents.strip())
            if kwargs.get("non_breaking", False):
                contents = re.sub(r' +', "~", contents)
            self.file.write(f"{contents}%\n")


class TeXTable(Table):
    def __init__(self, file: TextIOWrapper, **kwargs):
        self.file = file
        self.kwargs = kwargs

    def cols(self) -> int:
        return self.kwargs.get("cols", 2)  # Default is two columns

    def textwidth_ratio(self) -> float:
        return 1.0 / self.cols()

    def tabcolsep_ratio(self) -> float:
        if self.cols() <= 2:
            return 1.0
        else:
            return 1.0 + (1.0 / (self.cols() - 2))

    def col_format_desc(self) -> str:
        return f"p{{\\dimexpr {self.textwidth_ratio()}\\linewidth - {self.tabcolsep_ratio()}\\tabcolsep \\relax}}"

    def table_format_desc(self) -> str:
        return f"@{{\\zz}}{self.col_format_desc() * self.cols()}@{{}}"

    def __enter__(self):
        self.file.write(f"\\setbox\\ltmcbox\\vbox{{%\n")
        self.file.write(f"\\makeatletter\\col@number\\@ne%\n")
        self.file.write(f"\\resetLTcolor%\n")
        self.file.write(f"\\begin{{longtable}}{{{self.table_format_desc()}}}%\n")
        if "title" in self.kwargs:
            self.file.write(
                f"\\caption{{\\bf {tex_escape(self.kwargs['title'])}}} \\\\ \\hline%\n"
            )
        self.file.write(f"\\endhead%\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.write(f"\\end{{longtable}}%\n")
        self.file.write(f"\\unskip%\n")
        self.file.write(f"\\unpenalty%\n")
        self.file.write(f"\\unpenalty}}%\n")
        self.file.write(f"\\unvbox\\ltmcbox%\n")

    def row(self, **kwargs):
        return TeXRow(self.file, **kwargs)


class TeXSection(Section):
    def __init__(self, file: TextIOWrapper, **kwargs):
        self.file = file
        self.kwargs = kwargs

    def cols(self) -> int:
        return self.kwargs.get("cols", 1)  # Default is one column

    def __enter__(self):
        if "title" in self.kwargs:
            self.file.write(f"\\section{{{tex_escape(self.kwargs['title'])}}}%\n")
        if self.cols() > 1:
            self.file.write(f"\\begin{{multicols}}{{{self.cols()}}}%\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        if self.cols() > 1:
            self.file.write(f"\\end{{multicols}}%\n")
        if self.kwargs.get("clear_page_after_section", True):
            self.file.write(f"\\clearpage%\n")

    def table(self, **kwargs):
        return TeXTable(self.file, **kwargs)


class TeXDoc(Doc):
    def __init__(self, file_path: str, **kwargs):
        self.file = open(file_path, "w")
        self.kwargs = kwargs

    def __enter__(self):
        documentclass = self.kwargs.get("documentclass", "article")
        documentclass_options = self.kwargs.get("documentclass_options", "")
        self.file.write(
            f"\\documentclass[{documentclass_options}]{{{documentclass}}}%\n"
        )
        if "preamble_path" in self.kwargs:
            self.file.write(f"\\input{{{self.kwargs['preamble_path']}}}%\n")
        self.file.write(f"\\begin{{document}}%\n")
        if "title" in self.kwargs:
            self.file.write(f"\\begin{{center}}%\n")
            self.file.write(f"\\Huge\\bf%\n")
            self.file.write(f"{tex_escape(self.kwargs['title'])}%\n")
            self.file.write(f"\\end{{center}}%\n")
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.file.write(f"\\clearpage%\n")
        self.file.write(f"\\thispagestyle{{empty}}%\n")
        self.file.write(f"\\listoftables%\n")
        self.file.write(f"\\end{{document}}\n")
        self.file.close()

    def section(self, **kwargs):
        return TeXSection(self.file, **kwargs)
