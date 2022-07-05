from pathlib import Path
from george.types.python import *
from george.analysis.python.static_analysis import PythonStaticPackageAnalysis
from george.analysis.talon.static_analysis import TalonStaticPackageAnalysis
from george.analysis.talon.tree_sitter import TreeSitterTalon

build_dir = Path("build")
build_dir.mkdir(exist_ok=True)

knausj_talon_build_dir = build_dir / "knausj_talon"
knausj_talon_build_dir.mkdir(exist_ok=True)

package_root = Path("vendor/knausj_talon")
python_analyser = PythonStaticPackageAnalysis()
python_package_info = python_analyser.process_package(package_root)
(knausj_talon_build_dir / "python_package_info.json").write_text(python_package_info.to_json())

tree_sitter_talon = TreeSitterTalon(repository_path="vendor/tree-sitter-talon")
talon_analyser = TalonStaticPackageAnalysis(python_package_info, tree_sitter_talon)
talon_package_info = talon_analyser.process_package(package_root)
(knausj_talon_build_dir / "talon_package_info.json").write_text(talon_package_info.to_json())
