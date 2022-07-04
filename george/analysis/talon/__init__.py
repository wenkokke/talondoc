from pathlib import Path
import re
from typing import Generator
from sys import platform
from george.analysis.talon.description import *
from george.analysis.talon.script.describer import AbcTalonScriptDescriber
from george.analysis.info import *
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
        self.match_query = self.tree_sitter_talon.language.query("(match) @match")
        self.include_tags_query = self.tree_sitter_talon.language.query(
            "(include_tag) @include_tag"
        )
        self.setting_assignment_query = self.tree_sitter_talon.language.query(
            "(settings (block (assignment)* @assignment))"
        )
        self.action_query = self.tree_sitter_talon.language.query("(action) @action")
        self.capture_query = self.tree_sitter_talon.language.query("(capture) @capture")
        self.list_query = self.tree_sitter_talon.language.query("(list) @list")
        self.command_query = self.tree_sitter_talon.language.query("(command) @command")

    def required_tags(self, node: ts.Node) -> Generator[TalonDeclName, None, None]:
        captures = self.match_query.captures(node)
        if captures:
            for match_node, anchor in captures:
                assert anchor == "match"
                key_node = match_node.child_by_field_name("key")
                if key_node.text == b"tag":
                    pattern_node = match_node.child_by_field_name("pattern")
                    yield pattern_node.text.decode().strip()

    def included_tags(self, node: ts.Node) -> Generator[TalonDeclName, None, None]:
        captures = self.include_tags_query.captures(node)
        if captures:
            for include_tag_node, anchor in captures:
                assert anchor == "include_tag"
                tag_node = include_tag_node.child_by_field_name("tag")
                if tag_node:
                    yield tag_node.text.decode().strip()

    def referenced_settings(
        self, node: ts.Node
    ) -> Generator[TalonDeclName, None, None]:
        captures = self.setting_assignment_query.captures(node)
        if captures:
            for assignment, anchor in captures:
                assert anchor == "assignment"
                left = assignment.child_by_field_name("left")
                if left:
                    yield left.text.decode()

    def referenced_actions(self, node: ts.Node) -> Generator[TalonDeclName, None, None]:
        captures = self.action_query.captures(node)
        if captures:
            for action, anchor in captures:
                assert anchor == "action"
                action_name = action.child_by_field_name("action_name")
                if action_name:
                    yield action_name.text.decode()

    def referenced_captures(
        self, node: ts.Node
    ) -> Generator[TalonDeclName, None, None]:
        captures = self.capture_query.captures(node)
        if captures:
            for capture, anchor in captures:
                assert anchor == "capture"
                capture_name = capture.child_by_field_name("capture_name")
                if capture_name:
                    yield capture_name.text.decode()

    def referenced_lists(self, node: ts.Node) -> Generator[TalonDeclName, None, None]:
        captures = self.list_query.captures(node)
        if captures:
            for list, anchor in captures:
                assert anchor == "list"
                list_name = list.child_by_field_name("list_name")
                if list_name:
                    yield list_name.text.decode()

    def commands(self, node: ts.Node) -> Generator[TalonCommand, None, None]:
        captures = self.command_query.captures(node)
        if captures:
            for command, anchor in captures:
                assert anchor == "command"
                rule = command.child_by_field_name("rule")
                script = command.child_by_field_name("script")
                block_node = self.tree_sitter_talon.types.from_tree_sitter(script)
                desc = self.talon_script_describer.transform(block_node)
                yield TalonCommand(
                    rule=TalonRule(text=rule.text.decode()),
                    script=TalonScript(code=script.text.decode(), desc=desc.compile()),
                )
