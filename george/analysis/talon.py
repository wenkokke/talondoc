from dataclasses import dataclass
from pathlib import Path
import re
from typing import Generator
from tree_sitter import Language, Parser, Tree, TreeCursor
from sys import platform

from george.analysis.info import TalonDeclName


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

    def tags(self, tree: Tree) -> Generator[TalonDeclName, None, None]:
        query = self.language.query("(match) @match")
        captures = query.captures(tree.root_node)
        if captures:
            for match_node, anchor in captures:
                assert anchor == "match"
                key_node = match_node.child_by_field_name('key')
                if key_node.text == b'tag':
                    pattern_node = match_node.child_by_field_name('pattern')
                    yield pattern_node.text.decode('utf-8').strip()

    def tag_includes(self, tree: Tree) -> Generator[TalonDeclName, None, None]:
        query = self.language.query("(tag_include) @tag_include")
        captures = query.captures(tree.root_node)
        if captures:
            for tag_include_node, anchor in captures:
                assert anchor == "tag_include"
                key_node = tag_include_node.child_by_field_name('key')
                if key_node.text == b'tag':
                    pattern_node = tag_include_node.child_by_field_name('pattern')
                    yield pattern_node.text.decode('utf-8').strip()
