from pathlib import Path
from george.analysis.info import *
from george.analysis.python import PythonAnalyser
from george.analysis.talon import TalonAnalyser
from george.tree_sitter.node_types import *
from george.tree_sitter.talon import TreeSitterTalon
from george.tree_sitter.type_provider import *


python_analyser = PythonAnalyser()
python_package_info = python_analyser.process_package(Path("vendor/knausj_talon"))

tree_sitter_talon = TreeSitterTalon()
talon_analyser = TalonAnalyser(python_package_info, tree_sitter_talon)

for talon_file in Path("vendor").glob("**/*.talon"):
    talon_file_tree = tree_sitter_talon.parse(talon_file)
    for command in talon_analyser.commands(talon_file_tree.root_node):
        pass
