from pathlib import Path
from george.analysis.info import *
from george.analysis.python import PythonAnalyser
from george.analysis.talon import TalonAnalyser

python_analyser = PythonAnalyser()
python_package_info = python_analyser.process_package(Path("vendor/knausj_talon"))

talon_analyser = TalonAnalyser(python_package_info)
for talon_file in Path("vendor").glob("**/*.talon"):
    talon_file_tree = talon_analyser.parse(talon_file)
    for command in talon_analyser.commands(talon_file_tree):
        print(command)