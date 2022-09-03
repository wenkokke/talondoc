import sys

from docutils import nodes
from sphinx import addnodes
from sphinx.util.typing import OptionSpec

from ...entries import PackageEntry, TalonFileEntry
from ...util.logging import getLogger
from ...util.nodes import colspec, row, entry, table, tbody, tgroup, title
from ...util.typing import optional_str, optional_strlist
from .abc import TalonDocDirective
from .command import describe_command, describe_rule, include_command

_logger = getLogger(__name__)


class TalonCommandTableDirective(TalonDocDirective):

    has_content = False
    required_arguments = 0
    optional_arguments = 1
    option_spec: OptionSpec = {
        "package": optional_str,
        "include": optional_strlist,
        "exclude": optional_strlist,
    }
    final_argument_whitespace = False

    def find_package(self) -> PackageEntry:
        namespace = self.options.get("package")
        candidate = self.talon.currentpackage
        if candidate and (not namespace or candidate.namespace == namespace):
            return candidate
        candidate = self.talon.packages.get(namespace, None)
        if candidate:
            return candidate
        raise ValueError(f"Could not find package '{namespace}'")

    def find_file(self, sig: str) -> TalonFileEntry:
        # Find the package:
        try:
            package_entry = self.find_package()
        except ValueError as e:
            raise ValueError(f"Could not find file '{sig}'", e)

        # Find the file:
        for file in package_entry.files:
            if isinstance(file, TalonFileEntry):
                if (
                    sig == file.name
                    or sig == str(file.path)
                    or f"{sig}.talon" == file.name
                    or f"{sig}.talon" == str(file.path)
                ):
                    return file
        raise ValueError(f"Could not find file '{sig}'")

    def handle_signature(self, sig: str, signode: addnodes.desc_signature):
        exclude = self.options.get("exclude", ())
        include = self.options.get("include", ())
        file_entry = self.find_file(sig)
        signode += table(
            title(nodes.Text(file_entry.name.removesuffix(".talon"))),
            tgroup(
                colspec(colwidth=1),
                colspec(colwidth=1),
                tbody(
                    row(
                        entry(describe_rule(command)),
                        entry(describe_command(command, registry=self.talon)),
                    )
                    for command in file_entry.commands
                    if include_command(command, exclude=exclude, include=include)
                ),
                cols=2,
            ),
            classes="compact",
        )
