from dataclasses import dataclass
from pathlib import Path
import re
from typing import Generator
from tree_sitter import Language, Parser, Tree, TreeCursor
from sys import platform
from .info import TalonCommand, TalonDeclName, TalonRule, TalonScript


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
        self.parser = Parser()
        self.parser.set_language(self.language)

        self.match_query = self.language.query("(match) @match")
        self.include_tags_query = self.language.query("(include_tag) @include_tag")
        self.setting_assignment_query = self.language.query(
            "(settings (block (assignment)* @assignment))"
        )
        self.action_query = self.language.query("(action) @action")
        self.capture_query = self.language.query("(capture) @capture")
        self.list_query = self.language.query("(list) @list")
        self.command_query = self.language.query("(command) @command")

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

    def required_tags(self, tree: Tree) -> Generator[TalonDeclName, None, None]:
        captures = self.match_query.captures(tree.root_node)
        if captures:
            for match_node, anchor in captures:
                assert anchor == "match"
                key_node = match_node.child_by_field_name("key")
                if key_node.text == b"tag":
                    pattern_node = match_node.child_by_field_name("pattern")
                    yield pattern_node.text.decode("utf-8").strip()

    def included_tags(self, tree: Tree) -> Generator[TalonDeclName, None, None]:
        captures = self.include_tags_query.captures(tree.root_node)
        if captures:
            for include_tag_node, anchor in captures:
                assert anchor == "include_tag"
                tag_node = include_tag_node.child_by_field_name("tag")
                if tag_node:
                    yield tag_node.text.decode("utf-8").strip()

    def referenced_settings(self, tree: Tree) -> Generator[TalonDeclName, None, None]:
        captures = self.setting_assignment_query.captures(tree.root_node)
        if captures:
            for assignment, anchor in captures:
                assert anchor == "assignment"
                left = assignment.child_by_field_name("left")
                if left:
                    yield left.text.decode("utf-8")

    def referenced_actions(self, tree: Tree) -> Generator[TalonDeclName, None, None]:
        captures = self.action_query.captures(tree.root_node)
        if captures:
            for action, anchor in captures:
                assert anchor == "action"
                action_name = action.child_by_field_name("action_name")
                if action_name:
                    yield action_name.text.decode("utf-8")

    def referenced_captures(self, tree: Tree) -> Generator[TalonDeclName, None, None]:
        captures = self.capture_query.captures(tree.root_node)
        if captures:
            for capture, anchor in captures:
                assert anchor == "capture"
                capture_name = capture.child_by_field_name("capture_name")
                if capture_name:
                    yield capture_name.text.decode("utf-8")

    def referenced_lists(self, tree: Tree) -> Generator[TalonDeclName, None, None]:
        captures = self.list_query.captures(tree.root_node)
        if captures:
            for list, anchor in captures:
                assert anchor == "list"
                list_name = list.child_by_field_name("list_name")
                if list_name:
                    yield list_name.text.decode("utf-8")

    def commands(self, tree: Tree) -> Generator[TalonCommand, None, None]:
        captures = self.command_query.captures(tree.root_node)
        if captures:
            for command, anchor in captures:
                assert anchor == "command"
                rule = command.child_by_field_name("rule")
                script = command.child_by_field_name("script")
                yield TalonCommand(
                    rule=TalonRule(text=rule.text.decode('utf-8')),
                    script=TalonScript(text=script.text.decode('utf-8')),
                )
