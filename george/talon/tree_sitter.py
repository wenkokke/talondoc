from pathlib import Path
import re
from sys import platform
import sys
from typing import Optional, Union
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

    def parse(self, contents: bytes, has_header: Optional[bool] = None) -> ts.Tree:
        if has_header is None:
            has_header = contents.startswith(b"-\n") or (b"\n-\n" in contents)
        if not has_header:
            contents = b"-\n" + contents
        return self.parser.parse(contents)

    def parse_file(self, path: Path, has_header: Optional[bool] = None) -> ts.Tree:
        return self.parse(path.read_bytes(), has_header=has_header)


talon_library_path = globals().get("talon_library_path", None)
talon_repository_path = globals().get("talon_repository_path", None)
talon_node_types_path = globals().get("talon_node_types_path", None)
sys.modules[__name__] = TreeSitterTalon(
    library_path=talon_library_path,
    repository_path=talon_repository_path,
    node_types_path=talon_node_types_path,
)
