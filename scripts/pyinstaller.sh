#!/bin/bash

# See: https://stackoverflow.com/a/4774063
ROOT_DIR="$(dirname "$( cd -- "$(dirname "$0")" >/dev/null 2>&1 || exit ; pwd -P )" )"

# Install TalonDoc
pip install -q "${ROOT_DIR}"

# Install PyInstaller
pip install -q pyinstaller

# Install hidden modules
pip install -q myst_parser
pip install -q sphinx_rtd_theme
pip install -q sphinx_tabs

# Create main script:
mkdir -p "${ROOT_DIR}/bin"
echo 'import talondoc'     >  "${ROOT_DIR}/bin/__main__.py"
echo 'talondoc.talondoc()' >> "${ROOT_DIR}/bin/__main__.py"

# Compile TalonDoc with PyInstaller
pyinstaller                                                                                                    \
  --name "talondoc"                                                                                            \
  --distpath "bin"                                                                                             \
  --python-option "-X utf8"                                                                                    \
  --collect-data "tree_sitter_talon"                                                                           \
  --collect-data "talondoc"                                                                                    \
  --collect-data "sphinx"                                                                                      \
  --collect-data "sphinxcontrib"                                                                               \
  --collect-data "myst_parser"      --collect-submodules "myst_parser"      --hidden-import "myst_parser"      \
  --collect-data "sphinx_rtd_theme" --collect-submodules "sphinx_rtd_theme" --hidden-import "sphinx_rtd_theme" \
  --collect-data "sphinx_tabs"      --collect-submodules "sphinx_tabs"      --hidden-import "sphinx_tabs"      \
  --onefile                                                                                                    \
  "${ROOT_DIR}/bin/__main__.py"
