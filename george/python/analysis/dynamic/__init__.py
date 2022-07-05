from pathlib import Path

import importlib
import os
import sys


class PythonDynamicPackageAnalysis:
    @staticmethod
    def process_package(package_root: Path):
        class StubPathFinder(importlib.machinery.PathFinder):
            """
            Makes the stubs directory available under 'talon'.
            """

            @classmethod
            def find_spec(cls, fullname, path=None, target=None):
                curr_dir = os.path.dirname(__file__)
                if fullname == "talon" or fullname.startswith("talon."):
                    # Load talon stubs as talon module
                    import_path = os.path.join(curr_dir, "stubs")
                    return super().find_spec(fullname, [import_path])
                elif fullname == "knausj_talon" or fullname.startswith("knausj_talon"):
                    # Load user submodules
                    import_path = os.path.join(*package_root.parts[:-1])
                    return super().find_spec(fullname, [import_path])
                else:
                    # Allow normal sys.path stuff to handle everything else
                    return None

        # Add the StubPathFinder
        sys.meta_path.append(StubPathFinder)

        for file_path in package_root.glob("**/*.py"):
            file_path = file_path.relative_to(package_root)
            package_name = package_root.parts[-1]
            module_path = ".".join((package_name, *file_path.with_suffix('').parts))
            importlib.import_module(module_path, package=package_root.parts[-1])
