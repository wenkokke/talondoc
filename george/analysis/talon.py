from dataclasses import dataclass
from pathlib import Path
import re
from tree_sitter import Language, Parser, Tree
from sys import platform


@dataclass
class TalonAnalyser:
    library_path: str = {
        "linux": "build/talon.so",
        "darwin": "build/talon.dylib",
        "win32": "build/talon.dll",
    }[platform]
    repository_path: str = "vendor/tree-sitter-talon"

    def __init__(self):
        Language.build_library(self.library_path, [self.repository_path])
        self.language = Language(self.library_path, "talon")
        self.parser = parser = Parser()
        parser.set_language(self.language)

    def parse(self, path: Path) -> Tree:
        # Check for optional header separator
        has_header = False
        with path.open('r') as f:
            for ln in f.readlines():
                if re.match('^-$', ln):
                    has_header = True
        # Prepend header separator if missing
        file_bytes = path.read_bytes()
        if not has_header:
            file_bytes = b'-\n'.join((file_bytes,))
        # Parse the Talon file
        return self.parser.parse(file_bytes)


# KNAUSJ_TALON = Path.home().glob("Projects/knausj_talon/**/*.talon")

# for talon_file in KNAUSJ_TALON:
#   print(talon_file)
#   talon_file_bytes = talon_file.read_bytes()
#   tree = parser.parse(talon_file_bytes)
#   print(tree.root_node.sexp())
