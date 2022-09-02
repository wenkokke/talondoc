import dataclasses
from functools import singledispatchmethod
import typing

from talondoc.entries import ActionGroupEntry
from .desc import (
    Desc,
    StepTemplate,
    Value,
    Step,
    concat,
    from_docstring,
)
from ..analyze.registry import Registry
from tree_sitter_talon import (
    Node,
    TalonAction,
    TalonExpression,
    TalonBlock,
    TalonCommandDeclaration,
    TalonBinaryOperator,
    TalonExpressionStatement,
    TalonAssignmentStatement,
    TalonVariable,
    TalonKeyAction,
    TalonSleepAction,
    TalonParenthesizedExpression,
    TalonComment,
    TalonInteger,
    TalonFloat,
    TalonImplicitString,
    TalonString,
    TalonStringContent,
    TalonStringEscapeSequence,
)


@dataclasses.dataclass
class MissingDocumentation(Exception):
    """Exception raised when a docstring cannot be found"""

    name: str


NodeVar = typing.TypeVar("NodeVar", bound=Node)


def _only_child(
    children: typing.Sequence[typing.Union[NodeVar, TalonComment]]
) -> NodeVar:
    ret: typing.Optional[NodeVar] = None
    for child in children:
        if not isinstance(child, TalonComment):
            if __debug__ and ret:
                raise AssertionError(f"Multiple non-comments in {children}.")
            ret = child
            if not __debug__:
                break
    if ret is None:
        raise AssertionError(f"Only comments in {children}.")
    return ret


class TalonScriptDescriber:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    @singledispatchmethod
    def describe(self, ast: Node) -> typing.Optional[Desc]:
        raise TypeError(type(ast))

    @describe.register
    def _(self, ast: TalonCommandDeclaration) -> typing.Optional[Desc]:
        return self.describe(ast.script)

    @describe.register
    def _(self, ast: TalonBlock) -> typing.Optional[Desc]:
        buffer = []
        for child in ast.children:
            buffer.append(self.describe(child))
        return concat(*buffer)

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
        print(action_group_entry)
        if (
            action_group_entry
            and action_group_entry.default
            and action_group_entry.default.desc
        ):
            desc = from_docstring(action_group_entry.default.desc)
            if isinstance(desc, StepTemplate):
                args = tuple(
                    self.describe(arg)
                    for arg in ast.arguments.children
                    if isinstance(arg, TalonExpression)
                )
                if all(isinstance(arg, Value) for arg in args):
                    desc = desc(typing.cast(tuple[Value, ...], args))
            return desc
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
