from pathlib import Path
import re
from typing import Generator
from sys import platform
from george.analysis.talon.description import *
from george.analysis.talon.script.describer import *
from george.tree_sitter.node_types import NodeType
from george.tree_sitter.type_provider import TypeProvider


import tree_sitter as ts


class TreeSitterTalon:
    library_path: str = {
        "linux": "build/talon.so",
        "darwin": "build/talon.dylib",
        "win32": "build/talon.dll",
    }[platform]
    repository_path: str = "vendor/tree-sitter-talon"
    node_types_path: str = "src/node-types.json"

    def __init__(
        self,
        library_path: Optional[str] = None,
        repository_path: Optional[str] = None,
        node_types_path: Optional[str] = None,
    ):
        if library_path:
            self.library_path = library_path
        if repository_path:
            self.repository_path = repository_path
        if node_types_path:
            self.node_types_path = node_types_path

        # Build tree-sitter-talon
        ts.Language.build_library(self.library_path, [self.repository_path])
        self.language = ts.Language(self.library_path, "talon")
        self.parser = ts.Parser()
        self.parser.set_language(self.language)

        # Build tree-sitter node types
        with open(f"{self.repository_path}/{self.node_types_path}", "r") as fp:
            node_types = NodeType.schema().loads(fp.read(), many=True)
        self.types = TypeProvider("types", node_types)

    def parse(self, path: Path) -> ts.Tree:
        assert isinstance(path, Path)
        # Check for optional header separator
        has_header = False
        with path.open("r") as f:
            for ln in f.readlines():
                if re.match("^-$", ln):
                    has_header = True
        # Prepend header separator if missing
        file_bytes = path.read_bytes()
        if not has_header:
            file_bytes = b"-\n".join((file_bytes,))
        # Parse the Talon file
        return self.parser.parse(file_bytes)
