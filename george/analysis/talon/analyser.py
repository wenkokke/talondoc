from pathlib import Path
import re
from typing import Generator
from sys import platform
from george.analysis.talon.description import *
from george.analysis.talon.info import (
    Source,
    TalonCommand,
    TalonFileInfo,
    TalonPackageInfo,
    TalonRule,
    TalonScript,
)
from george.analysis.talon.script.describer import AbcTalonScriptDescriber
from george.analysis.python.info import *
from george.tree_sitter.node_types import NodeType
from george.tree_sitter.type_provider import TypeProvider
from george.tree_sitter.talon import TreeSitterTalon

import tree_sitter as ts


class TalonAnalyser:
    def __init__(
        self,
        python_package_info: PythonPackageInfo,
        tree_sitter_talon: TreeSitterTalon,
    ):
        self.python_package_info = python_package_info
        self.tree_sitter_talon = tree_sitter_talon

        # Build node describer
        self.talon_script_describer = type(
            "TalonScriptDescriber",
            (AbcTalonScriptDescriber, tree_sitter_talon.types.NodeTransformer),
            {"python_package_info": python_package_info},
        )()

        # Build queries
        self.queries = {
            query_key: self.tree_sitter_talon.language.query(query_str)
            for query_key, query_str in {
                "match": "(match) @match",
                "include_tag": "(include_tag) @include_tag",
                "assignment": "(settings (block (assignment)* @assignment))",
                "action": "(action) @action",
                "capture": "(capture) @capture",
                "list": "(list) @list",
                "command": "(command) @command",
            }.items()
        }

    def process_file(
        self, file_path: Path, package_root: Path = Path(".")
    ) -> TalonFileInfo:
        talon_file_analyser = TalonFileAnalyser(self, package_root / file_path)
        return TalonFileInfo(
            path=str(file_path),
            commands=list(talon_file_analyser.commands()),
            uses={
                "Action": talon_file_analyser.referenced_actions(),
                "Capture": talon_file_analyser.referenced_captures(),
                "List": talon_file_analyser.referenced_lists(),
                "Setting": talon_file_analyser.referenced_settings(),
            },
        )

    def process_package(
        self, package_root: Path = Path(".")
    ) -> dict[str, TalonFileInfo]:
        file_infos = {}
        for file_path in package_root.glob("**/*.talon"):
            file_path = file_path.relative_to(package_root)
            file_infos[str(file_path)] = self.process_file(file_path, package_root)
        return TalonPackageInfo(str(package_root), file_infos)


class TalonFileAnalyser:
    def __init__(self, talon_analyser: TalonAnalyser, file_path: Path):
        self.talon_analyser = talon_analyser
        self.file_path = file_path
        self.tree: Optional[ts.Tree] = None

    def get_tree(self) -> ts.Tree:
        if self.tree:
            return self.tree
        else:
            self.tree = self.talon_analyser.tree_sitter_talon.parse(self.file_path)
            return self.tree

    def required_tags(
        self, node: Optional[ts.Node] = None
    ) -> Generator[TalonDeclName, None, None]:
        if node is None:
            node = self.get_tree().root_node
        captures = self.talon_analyser.queries["match"].captures(node)
        if captures:
            for match_node, anchor in captures:
                assert anchor == "match"
                key_node = match_node.child_by_field_name("key")
                if key_node.text == b"tag":
                    pattern_node = match_node.child_by_field_name("pattern")
                    yield pattern_node.text.decode().strip()

    def included_tags(
        self, node: Optional[ts.Node] = None
    ) -> Generator[TalonDeclName, None, None]:
        if node is None:
            node = self.get_tree().root_node
        captures = self.talon_analyser.queries["include_tags"].captures(node)
        if captures:
            for include_tag_node, anchor in captures:
                assert anchor == "include_tag"
                tag_node = include_tag_node.child_by_field_name("tag")
                if tag_node:
                    yield tag_node.text.decode().strip()

    def referenced_settings(
        self, node: Optional[ts.Node] = None
    ) -> Generator[TalonDeclName, None, None]:
        if node is None:
            node = self.get_tree().root_node
        captures = self.talon_analyser.queries["setting_assignment"].captures(node)
        if captures:
            for assignment, anchor in captures:
                assert anchor == "assignment"
                left = assignment.child_by_field_name("left")
                if left:
                    yield left.text.decode()

    def referenced_actions(
        self, node: Optional[ts.Node] = None
    ) -> Generator[TalonDeclName, None, None]:
        if node is None:
            node = self.get_tree().root_node
        captures = self.talon_analyser.queries["action"].captures(node)
        if captures:
            for action, anchor in captures:
                assert anchor == "action"
                action_name = action.child_by_field_name("action_name")
                if action_name:
                    yield action_name.text.decode()

    def referenced_captures(
        self, node: Optional[ts.Node] = None
    ) -> Generator[TalonDeclName, None, None]:
        if node is None:
            node = self.get_tree().root_node
        captures = self.talon_analyser.queries["capture"].captures(node)
        if captures:
            for capture, anchor in captures:
                assert anchor == "capture"
                capture_name = capture.child_by_field_name("capture_name")
                if capture_name:
                    yield capture_name.text.decode()

    def referenced_lists(
        self, node: Optional[ts.Node] = None
    ) -> Generator[TalonDeclName, None, None]:
        if node is None:
            node = self.get_tree().root_node
        captures = self.talon_analyser.queries["list"].captures(node)
        if captures:
            for list, anchor in captures:
                assert anchor == "list"
                list_name = list.child_by_field_name("list_name")
                if list_name:
                    yield list_name.text.decode()

    def commands(
        self, node: Optional[ts.Node] = None
    ) -> Generator[TalonCommand, None, None]:
        if node is None:
            node = self.get_tree().root_node
        captures = self.talon_analyser.queries["command"].captures(node)
        if captures:
            for command, anchor in captures:
                assert anchor == "command"
                rule = command.child_by_field_name("rule")
                script = command.child_by_field_name("script")
                rule = TalonRule(
                    text=rule.text.decode(), source=Source.from_tree_sitter(rule)
                )
                desc = self.talon_analyser.talon_script_describer.transform(
                    self.talon_analyser.tree_sitter_talon.types.from_tree_sitter(script)
                )
                script = TalonScript(
                    text=script.text.decode(),
                    source=Source.from_tree_sitter(script),
                    desc=desc,
                )
                yield TalonCommand(
                    rule=rule,
                    script=script,
                    file_path=self.file_path,
                )
