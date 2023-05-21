from typing import Any, Callable, Optional, Type, TypeVar, cast

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

from .._util._compat_singledispatchmethod import singledispatchmethod
from .._util.logging import getLogger
from ..analysis.registry import Registry, data
from ..analysis.registry.data.abc import Data
from . import Description, Step, StepsTemplate, Value, concat, from_docstring

_LOGGER = getLogger(__name__)


NodeVar = TypeVar("NodeVar", bound=Node)


class TalonScriptDescriber:
    def __init__(
        self,
        registry: Registry,
        *,
        docstring_hook: Optional[Callable[[str, str], Optional[str]]] = None,
    ) -> None:
        self.registry = registry
        self.docstring_hook = docstring_hook or (lambda clsname, name: None)

    @singledispatchmethod  # type: ignore[misc]
    def describe(self, ast: Node) -> Optional[Description]:
        raise TypeError(type(ast))

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonCommandDeclaration) -> Optional[Description]:
        return self.describe(ast.right)

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonBlock) -> Optional[Description]:
        buffer = []
        for child in ast.children:
            buffer.append(self.describe(child))
        return concat(*buffer)

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonExpressionStatement) -> Optional[Description]:
        desc = self.describe(ast.expression)
        if isinstance(ast.expression, TalonString):
            return Step(desc=f'Insert "{desc}"')
        return desc

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonAssignmentStatement) -> Optional[Description]:
        right = self.describe(ast.right)
        return Step(f"Let <{ast.left.text}> be {right}")

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonBinaryOperator) -> Optional[Description]:
        left = self.describe(ast.left)
        right = self.describe(ast.right)
        return Value(f"{left} {ast.operator.text} {right}")

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonVariable) -> Optional[Description]:
        return Value(f"<{ast.text}>")

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonKeyAction) -> Optional[Description]:
        return Step(f"Press {ast.arguments.text.strip()}.")

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonSleepAction, **kwargs: Any) -> Optional[Description]:
        return None

    def get_docstring(
        self,
        cls: Type[Data],
        name: str,
    ) -> Optional[str]:
        # Try the docstring_hook:
        docstring = self.docstring_hook(cls.__name__, name)
        # Try the registry:
        docstring = docstring or self.registry.lookup_description(cls, name)
        return docstring

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonAction) -> Optional[Description]:
        # TODO: resolve self.*
        name = ast.action_name.text
        docstring = self.get_docstring(data.Action, name)
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

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonParenthesizedExpression) -> Optional[Description]:
        return self.describe(ast.get_child())

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonComment) -> Optional[Description]:
        return None

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonInteger) -> Optional[Description]:
        return Value(ast.text)

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonFloat) -> Optional[Description]:
        return Value(ast.text)

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonImplicitString) -> Optional[Description]:
        return Value(ast.text)

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonString) -> Optional[Description]:
        return concat(*(self.describe(child) for child in ast.children))

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonStringContent) -> Optional[Description]:
        return Value(ast.text)

    @describe.register  # type: ignore[misc]
    def _(self, ast: TalonStringEscapeSequence) -> Optional[Description]:
        return Value(ast.text)
