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
python_dynamic_package_info = python_dynamic_analysis.process()
# print(python_dynamic_package_info.to_json())

python_static_analysis = PythonStaticPackageAnalysis(package_root)
python_static_package_info = python_static_analysis.process()
# print(python_static_package_info.to_json())

python_package_info = python_dynamic_package_info | python_static_package_info

talon_static_analysis = TalonStaticPackageAnalysis(python_package_info, package_root)
talon_package_info = talon_static_analysis.process()
(knausj_talon_build_dir / "talon_package_info.json").write_text(
    talon_package_info.to_json()
)
