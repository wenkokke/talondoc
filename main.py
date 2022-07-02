from pathlib import Path
from george.analysis.info import *
from george.analysis.python import PythonAnalyser
from george.analysis.talon import TalonAnalyser

# python_analyser = PythonAnalyser()
# for python_file in Path("vendor").glob("**/*.py"):
#     python_file_info = python_analyser.process(python_file)
#     print(python_file_info)

talon_analyser = TalonAnalyser()
for talon_file in Path("vendor").glob("**/*.talon"):
    talon_file_tree = talon_analyser.parse(talon_file)
    for command in talon_analyser.commands(talon_file_tree):
        print(command)