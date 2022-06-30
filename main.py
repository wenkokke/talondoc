from pathlib import Path
from george.analysis.info import *
from george.analysis.python import *

for python_file in Path("vendor").glob("**/*.py"):
    python_file_info_1 = PythonInfoVisitor(python_file).process()
    print(python_file_info_1)
