import sys

from ...entries import PackageEntry, TalonFileEntry
from docutils import nodes
from .abc.talon import TalonObjectDescription
from sphinx.addnodes import desc_signature
from sphinx.util.typing import OptionSpec
from ...util.typing import optional_str, optional_strlist
from .command import handle_rule, handle_script


class TalonFileDirective(TalonObjectDescription):

    has_content = False
    required_arguments = 1
    optional_arguments = sys.maxsize
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
                if sig == file.name or sig == str(file.path):
                    return file
        raise ValueError(f"Could not find file '{sig}'")

    def handle_signature(self, sig: str, signode: desc_signature):
        file_entry = self.find_file(sig)
        title = file_entry.name.removesuffix(".talon")
        table = nodes.table()
        table['classes'].append('compact')

        # Table Header
        tgroup = nodes.tgroup()
        tgroup['cols'] = 1
        colspec = nodes.colspec()
        colspec['colwidth'] = 1
        tgroup += colspec
        thead = nodes.thead()
        row = nodes.row()
        entry = nodes.entry()
        paragraph = nodes.paragraph()
        paragraph += nodes.Text(title)
        entry += paragraph
        row += entry
        thead += row
        tgroup += thead
        table += tgroup

        # Table Body:
        tgroup = nodes.tgroup()
        tgroup['cols'] = 1
        colspec = nodes.colspec()
        colspec['colwidth'] = 1
        tgroup += colspec
        tbody = nodes.tbody()
        for command in file_entry.commands:
            row = nodes.row()
            entry = nodes.entry()
            paragraph = nodes.paragraph()
            paragraph += handle_rule(command)
            entry += paragraph
            row += entry
            tbody += row
        tgroup += tbody
        table += tgroup
        signode += table
