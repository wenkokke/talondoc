# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
from typing import Optional, Union
from collections.abc import Callable

project = "example"
copyright = "2022, Wen Kokke"
author = "Wen Kokke"
release = "0.1.3"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

sys.path.append(os.path.abspath("../.."))

extensions = ["talondoc.sphinx"]


# -- Options for TalonDoc ----------------------------------------------------

# TalonDocDocstringHook = Union[
#     Callable[[str, str], Optional[str]],
#     dict[str, dict[str, str]],
# ]

# def talondoc_docstring_hook(sort: str, name: str) -> Optional[str]:
#     return None
#

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

import sphinx_bootstrap_theme

html_theme = "bootstrap"
html_theme_path = sphinx_bootstrap_theme.get_html_theme_path()
html_theme_options = {
    "navbar_title": "TalonDoc",
    "navbar_sidebarrel": False,
    "navbar_pagenav": True,
    "navbar_links": [
        ("knausj_talon", "./knausj_talon/index"),
    ],
    "bootswatch_theme": "flatly",
}
