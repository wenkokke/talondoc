from pathlib import Path
from george.analysis.python.info import *
from george.analysis.python.analyser import PythonAnalyser
from george.analysis.talon.analyser import TalonAnalyser
from george.tree_sitter.node_types import *
from george.tree_sitter.talon import TreeSitterTalon
from george.tree_sitter.type_provider import *


package_root = Path("vendor/knausj_talon")
python_analyser = PythonAnalyser()
python_package_info = python_analyser.process_package(package_root)
# print(python_package_info.to_json())
# Path("knausj_talon.py_info.json").write_text(json)

tree_sitter_talon = TreeSitterTalon(repository_path="vendor/tree-sitter-talon")
talon_analyser = TalonAnalyser(python_package_info, tree_sitter_talon)
talon_package_info = talon_analyser.process_package(package_root)
print(talon_package_info.to_json())
# Path("knausj_talon.talon_info.json").write_text(json)
