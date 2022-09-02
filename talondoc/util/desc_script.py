import dataclasses
from functools import singledispatchmethod
import typing

from talondoc.entries import ActionGroupEntry
from .desc import (
    Desc,
    InvalidInterpolation,
    Value,
    Step,
    Steps,
    StepTemplate,
    concat,
    from_docstring,
)
from ..analyze.registry import Registry
from tree_sitter_talon import (
    Node,
    TalonAction,
    TalonBlock,
    TalonCommandDeclaration,
    TalonBinaryOperator,
    TalonExpressionStatement,
    TalonAssignmentStatement,
    TalonVariable,
    TalonKeyAction,
    TalonSleepAction,
    TalonExpression,
    TalonParenthesizedExpression,
    TalonArgumentList,
    TalonComment,
    TalonOperator,
    TalonIdentifier,
    TalonInteger,
    TalonFloat,
    TalonImplicitString,
    TalonString,
    TalonStringContent,
    TalonStringEscapeSequence,
)

import re
import docstring_parser as docstring
import docstring_parser.google as docstring_google


@dataclasses.dataclass
class MissingDocumentation(Exception):
    """Exception raised when a docstring cannot be found"""

    name: str


NodeVar = typing.TypeVar("NodeVar", bound=Node)


def _only_child(
    children: typing.Sequence[typing.Union[NodeVar, TalonComment]]
) -> NodeVar:
    for child in children:
        if not isinstance(child, TalonComment):
            return child
    raise AssertionError(f"Only comments in: {children}")


class TalonScriptDescriber:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    @singledispatchmethod
    def describe(self, ast: Node) -> typing.Optional[Desc]:
        raise TypeError(type(ast))

    @describe.register
    def _(self, ast: TalonCommandDeclaration) -> typing.Optional[Desc]:
        return concat(self.describe(child) for child in [*ast.children, ast.script])

    @describe.register
    def _(self, ast: TalonBlock) -> typing.Optional[Desc]:
        return concat(self.describe(child) for child in ast.children)

    @describe.register
    def _(self, ast: TalonExpressionStatement) -> typing.Optional[Desc]:
        return self.describe(ast.expression)

    @describe.register
    def _(self, ast: TalonAssignmentStatement) -> typing.Optional[Desc]:
        right = self.describe(ast.right)
        return Step(f"Let <{ast.left.text}> be {right}")

    @describe.register
    def _(self, ast: TalonBinaryOperator) -> typing.Optional[Desc]:
        left = self.describe(ast.left)
        right = self.describe(ast.right)
        return Value(f"{left} {ast.operator.text} {right}")

    @describe.register
    def _(self, ast: TalonVariable) -> typing.Optional[Desc]:
        return Value(f"<{ast.text}>")

    @describe.register
    def _(self, ast: TalonKeyAction) -> typing.Optional[Desc]:
        return Step(f"Press {ast.arguments.text.strip()}.")

    @describe.register
    def _(self, ast: TalonSleepAction, **kwargs) -> typing.Optional[Desc]:
        return None

    @describe.register
    def _(self, ast: TalonAction) -> typing.Optional[Desc]:
        # TODO: resolve self.*
        action_group_entry = typing.cast(
            typing.Optional[ActionGroupEntry],
            self.registry.lookup(f"action-group:{ast.action_name.text}"),
        )
        if (
            action_group_entry
            and action_group_entry.default
            and action_group_entry.default.desc
        ):
            return from_docstring(action_group_entry.default.desc)
        return None

    @describe.register
    def _(self, ast: TalonParenthesizedExpression) -> typing.Optional[Desc]:
        return self.describe(_only_child(ast.children))

    @describe.register
    def _(self, ast: TalonComment) -> typing.Optional[Desc]:
        return None

    @describe.register
    def _(self, ast: TalonInteger) -> typing.Optional[Desc]:
        return Value(ast.text)

    @describe.register
    def _(self, ast: TalonFloat) -> typing.Optional[Desc]:
        return Value(ast.text)

    @describe.register
    def _(self, ast: TalonImplicitString) -> typing.Optional[Desc]:
        return Value(ast.text)

    @describe.register
    def _(self, ast: TalonString) -> typing.Optional[Desc]:
        return concat(self.describe(child) for child in ast.children)

    @describe.register
    def _(self, ast: TalonStringContent) -> typing.Optional[Desc]:
        return Value(ast.text)

    @describe.register
    def _(self, ast: TalonStringEscapeSequence) -> typing.Optional[Desc]:
        return Value(ast.text)

    # def get_action_docstring(self, name: TalonName) -> str:
    #     decl = self.python_package_info.get_action_declaration(name)
    #     if decl and decl.desc:
    #         is_return = re.match("^[Rr]eturns? (.*)", decl.desc)
    #         if is_return:
    #             return Chunk(is_return.group(0))
    #         else:
    #             try:
    #                 docstring: Docstring = dsp.parse(decl.desc)
    #                 return Template(
    #                     template=docstring.short_description,
    #                     params=tuple(param.arg_name for param in docstring.params),
    #                 )
    #             except dsp.ParseError as e:
    #                 warn(
    #                     "".join(
    #                         [
    #                             f"Parse error in docstring for {decl.name} ",
    #                             f"in {decl.file_path}:{decl.source.position.line}:{decl.source.position.column}:\n",
    #                             str(e),
    #                         ]
    #                     )
    #                 )
    #                 return Line(decl.desc.splitlines()[0])
    #     raise MissingDocumentation(name)
