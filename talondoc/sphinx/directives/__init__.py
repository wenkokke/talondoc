from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Optional, cast

import sphinx.directives
from docutils import nodes
from sphinx import addnodes
from talonfmt import talonfmt
from tree_sitter_talon import TalonComment

from ...registry import Registry
from ...registry.entries.user import UserCommandEntry
from ...util.desc import InvalidInterpolation
from ...util.describer import TalonScriptDescriber
from ...util.logging import getLogger
from ...util.nodes import desc_content, desc_name, paragraph

_LOGGER = getLogger(__name__)

if TYPE_CHECKING:
    from talondoc.sphinx.domains import TalonDomain
else:
    TalonDomain = Any


class TalonDocDirective(sphinx.directives.SphinxDirective):
    @property
    def talon(self) -> TalonDomain:
        return cast(TalonDomain, self.env.get_domain("talon"))

    @property
    def docstring_hook(self) -> Callable[[str, str], Optional[str]]:
        docstring_hook = self.env.config["talondoc_docstring_hook"]
        if docstring_hook is None:

            def __docstring_hook(sort: str, name: str) -> Optional[str]:
                return None

            return __docstring_hook
        elif isinstance(docstring_hook, dict):

            def __docstring_hook(sort: str, name: str) -> Optional[str]:
                value = docstring_hook.get(sort, {}).get(name, None)
                assert value is None or isinstance(value, str)
                return value

            return __docstring_hook
        else:

            def __docstring_hook(sort: str, name: str) -> Optional[str]:
                value = docstring_hook(sort, name)  # type: ignore
                assert value is None or isinstance(value, str)
                return value

            return __docstring_hook

    def describe_rule(self, command: UserCommandEntry) -> nodes.Text:
        return nodes.Text(talonfmt(command.ast.left, safe=False))

    def try_describe_script_via_action_docstrings(
        self,
        command: UserCommandEntry,
        *,
        registry: Registry,
    ) -> Optional[nodes.Text]:
        """
        Describe the script using the docstrings on the actions used by the script.
        """
        try:
            describer = TalonScriptDescriber(
                registry, docstring_hook=self.docstring_hook
            )
            desc = describer.describe(command.ast)
            if desc:
                return nodes.Text(str(desc))
        except InvalidInterpolation as e:
            _LOGGER.exception(e)
        return None

    def try_describe_script_via_script_docstrings(
        self,
        command: UserCommandEntry,
    ) -> Optional[nodes.Text]:
        """
        Describe the script using the docstrings present in the script itself.
        """
        comments = []
        for child in command.ast.right.children:
            if isinstance(child, TalonComment):
                comment = child.text.strip()
                if comment.startswith("###"):
                    comments.append(comment.removeprefix("###").strip())
        if comments:
            return nodes.Text(" ".join(comments))
        else:
            return None

    def describe_script_via_code_block(
        self, command: UserCommandEntry
    ) -> addnodes.highlightlang:
        """
        Describe the script by including it as a code block.
        """
        code = talonfmt(command.ast.script, safe=False)
        literal_block = nodes.literal_block(code, code)
        literal_block["language"] = "python"
        return literal_block  # type: ignore

    def describe_script(
        self,
        command: UserCommandEntry,
        *,
        registry: Registry,
        include_script: bool,
    ) -> list[nodes.Element]:
        """
        Describe the script using the docstrings on the script, the docstrings on
        the actions, or finally by including it as a code block.
        """
        buffer = []

        # 1. Use the Talon docstrings in the command script. Talon docstrings are comments which start with ###.
        desc = self.try_describe_script_via_script_docstrings(command)

        # 2. Use the Python docstrings from the actions used in the command script.
        if desc is None:
            desc = self.try_describe_script_via_action_docstrings(
                command, registry=registry
            )

        # Append the description.
        if desc is not None:
            buffer.append(paragraph(nodes.Text(str(desc))))

        if desc is None or include_script:
            # 3. Include the command script.
            buffer.append(self.describe_script_via_code_block(command))

        return buffer

    def handle_command(
        self,
        command: UserCommandEntry,
        signode: addnodes.desc_signature,
        *,
        registry: Registry,
        include_script: bool,
    ) -> addnodes.desc_signature:
        signode += desc_name(self.describe_rule(command))
        signode += desc_content(
            *self.describe_script(
                command,
                registry=registry,
                include_script=include_script,
            )
        )
        return signode

    def describe_command(
        self,
        command: UserCommandEntry,
        *,
        registry: Registry,
        include_script: bool,
    ) -> addnodes.desc_signature:
        return self.handle_command(
            command,
            addnodes.desc_signature(),
            registry=registry,
            include_script=include_script,
        )


class TalonDocObjectDescription(sphinx.directives.ObjectDescription, TalonDocDirective):
    pass
