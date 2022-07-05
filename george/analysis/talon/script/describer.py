from logging import warn
from docstring_parser import Docstring
import docstring_parser.google as dsp
from george.analysis.python.info import PythonPackageInfo
from george.analysis.talon.description import *
from george.analysis.talon.info import *

import re


@dataclass(frozen=True)
class MissingDocumentation(Exception):
    """Exception raised when a doc string cannot be built"""

    sort_name: TalonSortName
    name: str


class AbcTalonScriptDescriber(ABC):
    python_package_info: PythonPackageInfo

    def get_docstring(self, sort_name: TalonSortName, name: TalonDeclName) -> str:
        decl = self.python_package_info.declaration(sort_name, name)
        if decl and decl.desc:
            is_return = re.match("^[Rr]eturns? (.*)", decl.desc)
            if is_return:
                return Chunk(is_return.group(0))
            else:
                try:
                    docstring: Docstring = dsp.parse(decl.desc)
                    return Template(
                        template=docstring.short_description,
                        params=tuple(param.arg_name for param in docstring.params),
                    )
                except dsp.ParseError as e:
                    warn(
                        "".join(
                            [
                                f"Parse error in docstring for {decl.name} ",
                                f"in {decl.file_path}:{decl.source.position.line}:{decl.source.position.column}:\n",
                                str(e),
                            ]
                        )
                    )
                    return Line(decl.desc.splitlines()[0])
        raise MissingDocumentation(sort_name, name)

    def transform_Block(self, children: list[Desc], **kwargs) -> Desc:
        return Lines(children)

    def transform_Expression(self, expression: Desc, **kwargs) -> Desc:
        return expression

    def transform_Assignment(self, left: Desc, right: Desc, **kwargs) -> Desc:
        try:
            return Line(f"Let <{left}> be {right}")
        except InvalidInterpolation:
            return right

    def transform_BinaryOperator(
        self, left: Desc, operator: Desc, right: Desc, **kwargs
    ) -> Desc:
        return Chunk(f"{left} {operator} {right}")

    def transform_Variable(self, variable_name: Desc, **kwargs) -> Desc:
        return Chunk(f"<{variable_name}>")

    def transform_KeyAction(self, arguments: Desc, **kwargs) -> Desc:
        return Line(f"Press {arguments}")

    def transform_SleepAction(self, **kwargs) -> Desc:
        return Ignore()

    def transform_Action(
        self, action_name: Desc, arguments: list[Desc], **kwargs
    ) -> Desc:
        try:
            docstring = self.get_docstring("Action", str(action_name))
            if isinstance(docstring, Template):
                if isinstance(arguments, Lines):
                    return docstring(arguments.lines)
                else:
                    warn(f"Desc for ArgumentList must be Lines, found: {repr(arguments)}")
            else:
                return docstring
        except MissingDocumentation as e:
            return action_name

    def transform_ParenthesizedExpression(self, expression: Desc, **kwargs) -> Desc:
        return expression

    def transform_ArgumentList(self, children: list[Desc], **kwargs) -> Desc:
        return Lines(children)

    def transform_Comment(self, **kwargs) -> Desc:
        return Ignore()

    def transform_Operator(self, text: str, **kwargs) -> Desc:
        return Chunk(text)

    def transform_Identifier(self, text: str, **kwargs) -> Desc:
        return Chunk(text)

    def transform_Integer(self, text: str, **kwargs) -> Desc:
        return Chunk(text)

    def transform_Float(self, text: str, **kwargs) -> Desc:
        return Chunk(text)

    def transform_ImplicitString(self, text: str, **kwargs) -> Desc:
        return Chunk(text)

    def transform_String(self, children: list[Desc], **kwargs) -> Desc:
        if children:
            return Chunk("".join(map(str, children)))
        else:
            return Chunk("")

    def transform_StringContent(self, text: str, **kwargs) -> Desc:
        return Chunk(text)

    def transform_StringEscapeSequence(self, text: str, **kwargs) -> Desc:
        return Chunk(text)
