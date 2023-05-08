import sys
from typing import List

from sphinx import addnodes
from sphinx.util.typing import OptionSpec
from typing_extensions import override

from ...._util.logging import getLogger
from ..._util.typing import flag, optional_strlist
from ..errors import AmbiguousSignature, UnmatchedSignature
from .abc import TalonDocCommandDescription

_LOGGER = getLogger(__name__)


class TalonCommandDirective(TalonDocCommandDescription):
    has_content = True
    required_arguments = 1
    optional_arguments = sys.maxsize
    option_spec: OptionSpec = {
        "context": optional_strlist,
        "contexts": optional_strlist,
        "always_include_script": flag,
    }
    final_argument_whitespace = False

    @override
    def get_signatures(self) -> List[str]:
        return [" ".join(self.arguments)]

    @override
    def handle_signature(self, sig: str, signode: addnodes.desc_signature):
        try:
            command = self.find_command(sig, fullmatch=False, restrict_to=self.contexts)
            signode = self.describe_command(
                command,
                signode,
                always_include_script=self.always_include_script,
                docstring_hook=self.docstring_hook,
            )
            return command.name
        except (UnmatchedSignature, AmbiguousSignature) as e:
            _LOGGER.error(e)
            raise ValueError(e)
