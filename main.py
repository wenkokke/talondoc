from pathlib import Path
from typing import TypeVar
from george.analysis.info import *
from george.analysis.python import PythonAnalyser
from george.analysis.talon import TalonAnalyser
from george.tree_sitter import *

# python_analyser = PythonAnalyser()
# python_package_info = python_analyser.process_package(Path("vendor/knausj_talon"))
# python_package_info = PythonPackageInfo(Path("vendor/knausj_talon"))

# talon_analyser = TalonAnalyser(python_package_info)
# for talon_file in Path("vendor").glob("**/*.talon"):
#     talon_file_tree = talon_analyser.parse(talon_file)
#     visitor = TreeSitterVisitor()
#     visitor.generic_visit(talon_file_tree.root_node)
#     break


with open("vendor/tree-sitter-talon/src/node-types.json", 'r') as fp:
    node_types = NodeType.schema().loads(fp.read(), many=True)

Talon = TypeProvider("Talon", node_types=node_types)

python_package_info = PythonPackageInfo(package_root="vendor/knausj_talon")

talon_analyser = TalonAnalyser(python_package_info)
for talon_file in Path("vendor").glob("**/*.talon"):
    talon_file_tree = talon_analyser.parse(talon_file)
    source_file = Talon.parse(talon_file_tree.root_node)
    print(source_file)