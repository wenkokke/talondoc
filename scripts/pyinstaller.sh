#!/bin/bash

# See: https://stackoverflow.com/a/4774063
ROOT_DIR="$(dirname "$( cd -- "$(dirname "$0")" >/dev/null 2>&1 || exit ; pwd -P )" )"

# Create a virtual environment:
python -m venv "${ROOT_DIR}/.venv"

# Activate the virtual environment:
source "${ROOT_DIR}/.venv/bin/activate"

# Install TalonDoc
pip install "${ROOT_DIR}"

# Install PyInstaller
pip install pyinstaller

# Install hidden modules
pip install myst_parser
pip install sphinx_rtd_theme
pip install sphinx_tabs

# Compile TalonDoc with PyInstaller
pyinstaller                                                                                                    \
  --collect-data "tree_sitter_talon"                                                                           \
  --collect-data "talondoc"                                                                                    \
  --collect-data "sphinx"                                                                                      \
  --collect-data "sphinxcontrib"                                                                               \
  --collect-data "myst_parser"      --collect-submodules "myst_parser"      --hidden-import "myst_parser"      \
  --collect-data "sphinx_rtd_theme" --collect-submodules "sphinx_rtd_theme" --hidden-import "sphinx_rtd_theme" \
  --collect-data "sphinx_tabs"      --collect-submodules "sphinx_tabs"      --hidden-import "sphinx_tabs"      \
  --onefile                                                                                                    \
  "${ROOT_DIR}/.venv/bin/talondoc"
