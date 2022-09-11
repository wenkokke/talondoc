from collections.abc import Callable
from typing import Optional, Sequence, Union, TypeVar, cast
from functools import singledispatchmethod

from tree_sitter_talon import (
    Node,
    TalonAction,
    TalonAssignmentStatement,
    TalonBinaryOperator,
    TalonBlock,
    TalonCommandDeclaration,
    TalonComment,
    TalonExpression,
    TalonExpressionStatement,
    TalonFloat,
    TalonImplicitString,
    TalonInteger,
    TalonKeyAction,
    TalonParenthesizedExpression,
    TalonSleepAction,
    TalonString,
    TalonStringContent,
    TalonStringEscapeSequence,
    TalonVariable,
)

from talondoc.analyze.entries import ActionGroupEntry

from ..analyze.registry import Registry
from ..util.logging import getLogger
from .desc import Desc, Step, StepsTemplate, Value, concat, from_docstring

_logger = getLogger(__name__)


NodeVar = TypeVar("NodeVar", bound=Node)


def _only_child(children: Sequence[Union[NodeVar, TalonComment]]) -> NodeVar:
    ret: Optional[NodeVar] = None
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
    def __init__(
        self,
        registry: Registry,
        *,
        custom_docstring_hook: Optional[Callable[[str], Optional[str]]] = None,
    ) -> None:
        self.registry = registry
        self.custom_docstring_hook = custom_docstring_hook

    def get_docstring(
        self, qualified_name: str, *, namespace: Optional[str] = None
    ) -> Optional[str]:
        desc: Optional[str]
        if self.custom_docstring_hook:
            desc = self.custom_docstring_hook(qualified_name)
            if desc:
                return desc
        obj = self.registry.lookup(qualified_name, namespace=namespace)
        if obj:
            return obj.get_docstring()
        return None

    @singledispatchmethod
    def describe(self, ast: Node) -> Optional[Desc]:
        raise TypeError(type(ast))

    @describe.register
    def _(self, ast: TalonCommandDeclaration) -> Optional[Desc]:
        return self.describe(ast.script)

    @describe.register
    def _(self, ast: TalonBlock) -> Optional[Desc]:
        buffer = []
        for child in ast.children:
            buffer.append(self.describe(child))
        return concat(*buffer)

    @describe.register
    def _(self, ast: TalonExpressionStatement) -> Optional[Desc]:
        desc = self.describe(ast.expression)
        if isinstance(ast.expression, TalonString):
            return Step(desc=f'Insert "{desc}"')
        return desc

    @describe.register
    def _(self, ast: TalonAssignmentStatement) -> Optional[Desc]:
        right = self.describe(ast.right)
        return Step(f"Let <{ast.left.text}> be {right}")

    @describe.register
    def _(self, ast: TalonBinaryOperator) -> Optional[Desc]:
        left = self.describe(ast.left)
        right = self.describe(ast.right)
        return Value(f"{left} {ast.operator.text} {right}")

    @describe.register
    def _(self, ast: TalonVariable) -> Optional[Desc]:
        return Value(f"<{ast.text}>")

    @describe.register
    def _(self, ast: TalonKeyAction) -> Optional[Desc]:
        return Step(f"Press {ast.arguments.text.strip()}.")

    @describe.register
    def _(self, ast: TalonSleepAction, **kwargs) -> Optional[Desc]:
        return None

    @describe.register
    def _(self, ast: TalonAction) -> Optional[Desc]:
        # TODO: resolve self.*
        docstring = self.get_docstring(f"action-group:{ast.action_name.text}")
        if docstring:
            desc = from_docstring(docstring)
            if isinstance(desc, StepsTemplate):
                desc = desc(
                    tuple(
                        self.describe(arg)
                        for arg in ast.arguments.children
                        if isinstance(arg, TalonExpression)
                    )
                )
            return desc
        return None

    @describe.register
    def _(self, ast: TalonParenthesizedExpression) -> Optional[Desc]:
        return self.describe(_only_child(ast.children))

    @describe.register
    def _(self, ast: TalonComment) -> Optional[Desc]:
        return None

    @describe.register
    def _(self, ast: TalonInteger) -> Optional[Desc]:
        return Value(ast.text)

    @describe.register
    def _(self, ast: TalonFloat) -> Optional[Desc]:
        return Value(ast.text)

    @describe.register
    def _(self, ast: TalonImplicitString) -> Optional[Desc]:
        return Value(ast.text)

    @describe.register
    def _(self, ast: TalonString) -> Optional[Desc]:
        return concat(*(self.describe(child) for child in ast.children))

    @describe.register
    def _(self, ast: TalonStringContent) -> Optional[Desc]:
        return Value(ast.text)

    @describe.register
    def _(self, ast: TalonStringEscapeSequence) -> Optional[Desc]:
        return Value(ast.text)
