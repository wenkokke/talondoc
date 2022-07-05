from pathlib import Path
from george.analysis.python.info import *
from george.analysis.python.analyser import PythonAnalyser
from george.analysis.talon.analyser import TalonAnalyser
from george.tree_sitter.node_types import *
from george.tree_sitter.talon import TreeSitterTalon
from george.tree_sitter.type_provider import *

build_dir = Path("build")
build_dir.mkdir(exist_ok=True)

knausj_talon_build_dir = build_dir / "knausj_talon"
knausj_talon_build_dir.mkdir(exist_ok=True)

package_root = Path("vendor/knausj_talon")
python_analyser = PythonAnalyser()
python_package_info = python_analyser.process_package(package_root)
(knausj_talon_build_dir / "python_package_info.json").write_text(python_package_info.to_json())

tree_sitter_talon = TreeSitterTalon(repository_path="vendor/tree-sitter-talon")
talon_analyser = TalonAnalyser(python_package_info, tree_sitter_talon)
talon_package_info = talon_analyser.process_package(package_root)
(knausj_talon_build_dir / "talon_package_info.json").write_text(talon_package_info.to_json())
