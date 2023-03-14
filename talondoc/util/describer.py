from collections.abc import Callable
from functools import singledispatchmethod
from typing import Optional, Sequence, TypeVar, Union, cast

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

from ..analyze.entries.abc import GroupableObject
from ..analyze.entries.user import UserActionEntry, UserTagEntry
from ..analyze.registry import Registry
from .desc import Desc, Step, StepsTemplate, Value, concat, from_docstring
from .logging import getLogger

_LOGGER = getLogger(__name__)


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
        docstring_hook: Optional[Callable[[str, str], Optional[str]]] = None,
    ) -> None:
        self.registry = registry
        self.docstring_hook = docstring_hook

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

    def get_docstring(
        self, sort: Union[type[UserTagEntry], type[GroupableObject]], name: str
    ) -> Optional[str]:
        if self.docstring_hook:
            docstring = self.docstring_hook(sort.sort, name)
            if docstring:
                return docstring
        entry = self.registry.lookup(sort, name)
        if entry is not None:
            return entry.get_docstring()
        return None

    @describe.register
    def _(self, ast: TalonAction) -> Optional[Desc]:
        # TODO: resolve self.*
        name = ast.action_name.text
        docstring = self.get_docstring(UserActionEntry, name)
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
