from pathlib import Path
from george.python.analysis.dynamic import PythonDynamicPackageAnalysis
from george.python.analysis.static import PythonStaticPackageAnalysis
from george.talon.analysis.static import TalonStaticPackageAnalysis
from george.types import merged

build_dir = Path("build")
build_dir.mkdir(exist_ok=True)

knausj_talon_build_dir = build_dir / "knausj_talon"
knausj_talon_build_dir.mkdir(exist_ok=True)

package_root = Path("examples/knausj_talon").absolute()

python_dynamic_analysis = PythonDynamicPackageAnalysis(package_root)
python_dynamic_package_info = python_dynamic_analysis.process()

python_static_analysis = PythonStaticPackageAnalysis(package_root)
python_static_package_info = python_static_analysis.process()

python_package_info = python_dynamic_package_info.merged_with(python_static_package_info)
(knausj_talon_build_dir / "python_package_info.json").write_text(
    python_package_info.to_json()
)
talon_static_analysis = TalonStaticPackageAnalysis(python_package_info, package_root)
talon_package_info = talon_static_analysis.process()
(knausj_talon_build_dir / "talon_package_info.json").write_text(
    talon_package_info.to_json()
)
