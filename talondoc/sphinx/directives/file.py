from .abc.talon import TalonObjectDescription
from docutils.nodes import Element


class TalonFileDirective(TalonObjectDescription):

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False

    def run(self) -> list[Element]:
        pass