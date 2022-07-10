from pathlib import Path
from george.python.analysis.dynamic import PythonDynamicPackageAnalysis
from george.python.analysis.static import PythonStaticPackageAnalysis
from george.talon.analysis.static import TalonStaticPackageAnalysis

build_dir = Path("build")
build_dir.mkdir(exist_ok=True)

knausj_talon_build_dir = build_dir / "knausj_talon"
knausj_talon_build_dir.mkdir(exist_ok=True)

package_root = Path("vendor/knausj_talon").absolute()

python_dynamic_analysis = PythonDynamicPackageAnalysis(package_root)
python_dynamic_analysis.process()

package_info = python_dynamic_analysis.python_package_info
for file_name, file_info in package_info.file_infos.items():
    for sort_name, overrides_for_sort_name in file_info.overrides.items():
        for decl_name, overrides_for_decl_name in overrides_for_sort_name.items():
            for decl in overrides_for_decl_name:
                if type(decl.matches) != bool:
                    print(repr(decl.matches))

# python_static_analysis = PythonStaticPackageAnalysis()
# python_package_info = python_static_analysis.process_package(package_root)
# (knausj_talon_build_dir / "python_package_info.json").write_text(
#     python_package_info.to_json()
# )

# tree_sitter_talon = TreeSitterTalon(repository_path="vendor/tree-sitter-talon")
# talon_static_analysis = TalonStaticPackageAnalysis(python_package_info, tree_sitter_talon)
# talon_package_info = talon_static_analysis.process_package(package_root)
# (knausj_talon_build_dir / "talon_package_info.json").write_text(
#     talon_package_info.to_json()
# )
