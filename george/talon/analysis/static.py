from pathlib import Path
from typing import Generator, Optional
from george.talon.analysis.script_describer import AbcTalonScriptDescriber
from george.types import *

import tree_sitter as ts
import tree_sitter_talon as talon


MATCH_QUERY = talon.language.query("(match) @match")
INCLUDE_TAGS_QUERY = talon.language.query("(include_tag) @include_tag")
SETTING_ASSIGNMENT_QUERY = talon.language.query(
    "(settings (block (assignment)* @setting_assignment))"
)
ACTION_QUERY = talon.language.query("(action) @action")
CAPTURE_QUERY = talon.language.query("(capture) @capture")
LIST_QUERY = talon.language.query("(list) @list")
COMMAND_QUERY = talon.language.query("(command) @command")


@dataclass
class TalonScriptDescriber(AbcTalonScriptDescriber, talon.types.NodeTransformer):
    python_package_info: PythonPackageInfo


class TalonStaticPackageAnalysis:
    def __init__(
        self, python_package_info: PythonPackageInfo, package_root: Path = Path(".")
    ):
        self.package_root = package_root
        self.script_describer = TalonScriptDescriber(python_package_info)

    def process(self) -> dict[str, TalonFileInfo]:
        file_infos = {}
        for file_path in self.package_root.glob("**/*.talon"):
            file_path = file_path.relative_to(self.package_root)
            file_infos[str(file_path)] = TalonStaticFileAnalysis(
                file_path, self.package_root, self.script_describer
            ).process()
        return TalonPackageInfo(
            file_infos=file_infos,
        )


class TalonStaticFileAnalysis:
    def __init__(
        self,
        file_path: Path,
        package_root: Path,
        script_describer: TalonScriptDescriber,
    ):
        self.file_path = file_path
        self.package_root = package_root
        self.script_describer = script_describer
        self._tree: Optional[ts.Tree] = None

    def process(self) -> TalonFileInfo:
        return TalonFileInfo(
            file_path=str(self.file_path),
            commands=list(self.commands()),
            uses={
                "Action": list(self.referenced_actions()),
                "Capture": list(self.referenced_captures()),
                "List": list(self.referenced_lists()),
                "Setting": list(self.referenced_settings()),
            },
        )

    @property
    def tree(self) -> ts.Tree:
        if self._tree:
            return self._tree
        else:
            self._tree = talon.parse_file(self.package_root / self.file_path)
            return self._tree

    def required_tags(
        self, node: Optional[ts.Node] = None
    ) -> Generator[TalonName, None, None]:
        if node is None:
            node = self.tree.root_node
        captures = MATCH_QUERY.captures(node)
        if captures:
            for match_node, anchor in captures:
                assert anchor == "match"
                key_node = match_node.child_by_field_name("key")
                if key_node.text == b"tag":
                    pattern_node = match_node.child_by_field_name("pattern")
                    yield pattern_node.text.decode("utf-8").strip()

    def included_tags(
        self, node: Optional[ts.Node] = None
    ) -> Generator[TalonName, None, None]:
        if node is None:
            node = self.tree.root_node
        captures = INCLUDE_TAGS_QUERY.captures(node)
        if captures:
            for include_tag_node, anchor in captures:
                assert anchor == "include_tag"
                tag_node = include_tag_node.child_by_field_name("tag")
                if tag_node:
                    yield tag_node.text.decode("utf-8").strip()

    def referenced_settings(
        self, node: Optional[ts.Node] = None
    ) -> Generator[TalonName, None, None]:
        if node is None:
            node = self.tree.root_node
        captures = SETTING_ASSIGNMENT_QUERY.captures(node)
        if captures:
            for assignment, anchor in captures:
                assert anchor == "setting_assignment"
                left = assignment.child_by_field_name("left")
                if left:
                    yield left.text.decode("utf-8")

    def referenced_actions(
        self, node: Optional[ts.Node] = None
    ) -> Generator[TalonName, None, None]:
        if node is None:
            node = self.tree.root_node
        captures = ACTION_QUERY.captures(node)
        if captures:
            for action, anchor in captures:
                assert anchor == "action"
                action_name = action.child_by_field_name("action_name")
                if action_name:
                    yield action_name.text.decode("utf-8")

    def referenced_captures(
        self, node: Optional[ts.Node] = None
    ) -> Generator[TalonName, None, None]:
        if node is None:
            node = self.tree.root_node
        captures = CAPTURE_QUERY.captures(node)
        if captures:
            for capture, anchor in captures:
                assert anchor == "capture"
                capture_name = capture.child_by_field_name("capture_name")
                if capture_name:
                    yield capture_name.text.decode("utf-8")

    def referenced_lists(
        self, node: Optional[ts.Node] = None
    ) -> Generator[TalonName, None, None]:
        if node is None:
            node = self.tree.root_node
        captures = LIST_QUERY.captures(node)
        if captures:
            for list, anchor in captures:
                assert anchor == "list"
                list_name = list.child_by_field_name("list_name")
                if list_name:
                    yield list_name.text.decode("utf-8")

    def commands(
        self, node: Optional[ts.Node] = None
    ) -> Generator[TalonCommand, None, None]:
        if node is None:
            node = self.tree.root_node
        captures = COMMAND_QUERY.captures(node)
        if captures:
            for command, anchor in captures:
                assert anchor == "command"
                rule = command.child_by_field_name("rule")
                script = command.child_by_field_name("script")
                rule = TalonRule(
                    rule=talon.types.from_tree_sitter(rule),
                    source=Source.from_tree_sitter(self.file_path, rule),
                )
                desc = talon.types.from_tree_sitter(script)
                desc = self.script_describer.transform(desc).compile()
                script = TalonScript(
                    source=Source.from_tree_sitter(self.file_path, script),
                    desc=desc,
                )
                yield TalonCommand(
                    rule=rule,
                    script=script,
                )
