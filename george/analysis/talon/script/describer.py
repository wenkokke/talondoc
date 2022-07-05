from logging import warn
from docstring_parser import Docstring
from docstring_parser.google import ParseError, parse
from george.analysis.python.info import PythonPackageInfo
from george.analysis.talon.description import *
from george.analysis.talon.info import *
from george.tree_sitter.type_provider import Hist

import re
import tree_sitter as ts

DescHist = Hist[Desc, ts.Node]


@dataclass(frozen=True)
class MissingDocumentation(Exception):
    """Exception raised when a doc string cannot be built"""

    sort: TalonSort
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
                    docstring: Docstring = parse(decl.desc)
                    return Template(
                        template=docstring.short_description,
                        params=tuple(param.arg_name for param in docstring.params),
                    )
                except ParseError as e:
                    warn(e)
                    return Line(decl.desc.splitlines()[0])
        raise MissingDocumentation(sort_name, name)

    def transform_Block(self, text: str, children: list[DescHist], **kwargs) -> Desc:
        return Lines([child.value for child in children])

    def transform_Expression(self, text: str, expression: DescHist, **kwargs) -> Desc:
        return expression.value

    def transform_Assignment(
        self, text: str, left: DescHist, right: DescHist, **kwargs
    ) -> Desc:
        try:
            return Line(f"Let <{left}> be {right}")
        except InvalidInterpolation:
            return right.value

    def transform_BinaryOperator(
        self, text: str, left: DescHist, operator: DescHist, right: DescHist, **kwargs
    ) -> Desc:
        return Chunk(f"{left} {operator} {right}")

    def transform_Variable(self, text: str, variable_name: DescHist, **kwargs) -> Desc:
        return Chunk(f"<{variable_name}>")

    def transform_KeyAction(self, text: str, arguments: DescHist, **kwargs) -> Desc:
        return Line(f"Press {arguments}")

    def transform_SleepAction(self, text: str, arguments: DescHist, **kwargs) -> Desc:
        return Ignore()

    def transform_Action(
        self, text: str, action_name: DescHist, arguments: list[DescHist], **kwargs
    ) -> Desc:
        try:
            docstring = self.get_docstring("Action", str(action_name.value))
            if isinstance(docstring, Template):
                return docstring(arguments)
            else:
                return docstring
        except MissingDocumentation as e:
            return action_name.value

    def transform_ParenthesizedExpression(
        self, text: str, expression: DescHist, **kwargs
    ) -> Desc:
        return expression.value

    def transform_ArgumentList(
        self, text: str, children: list[DescHist], **kwargs
    ) -> Desc:
        return Lines([child.value for child in children])

    def transform_Comment(self, text: str, **kwargs) -> Desc:
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

    def transform_String(self, text: str, children: list[DescHist], **kwargs) -> Desc:
        if children:
            return Chunk("".join(str(child.value) for child in children))
        else:
            return Chunk("")

    def transform_StringContent(self, text: str, **kwargs) -> Desc:
        return Chunk(text)

    def transform_StringEscapeSequence(self, text: str, **kwargs) -> Desc:
        return Chunk(text)
