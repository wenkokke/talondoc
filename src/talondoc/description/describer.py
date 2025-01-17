from collections.abc import Callable
from typing import TypeVar

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
        docstring_hook: Callable[[str, str], str | None] | None = None,
    ) -> None:
        self.registry = registry
        self.docstring_hook = docstring_hook or (lambda clsname, name: None)

    def get_docstring(
        self,
        cls: type[Data],
        name: str,
    ) -> str | None:
        # Try the docstring_hook:
        docstring = self.docstring_hook(cls.__name__, name)
        # Try the registry:
        docstring = docstring or self.registry.lookup_description(cls, name)
        return docstring

    def describe(self, ast: Node) -> Description | None:
        match ast:
            case TalonSleepAction() | TalonComment():
                return None

            case (
                TalonFloat()
                | TalonInteger()
                | TalonImplicitString()
                | TalonStringContent()
                | TalonStringEscapeSequence()
                | TalonStringContent()
            ):
                return Value(ast.text)

            #  Nodes that use format strings
            case TalonBinaryOperator():
                return Value(
                    f"{self.describe(ast.left)} {ast.operator.text} {self.describe(ast.right)}"  # noqa: E501
                )
            case TalonExpressionStatement() if isinstance(ast.expression, TalonString):
                return Step(desc=f'Insert "{self.describe(ast.expression)}"')
            case TalonAssignmentStatement():
                return Step(f"Let <{ast.left.text}> be {self.describe(ast.right)}")
            case TalonVariable():
                return Value(f"<{ast.text}>")
            case TalonKeyAction():
                # Todo: maybe add way to render keypress
                return Step(f"Press {ast.arguments.text.strip()}.")

            # Nodes with Children
            case TalonExpressionStatement():
                return self.describe(ast.expression)
            case TalonCommandDeclaration():
                return self.describe(ast.right)
            case TalonParenthesizedExpression():
                return self.describe(ast.get_child())
            case TalonBlock() | TalonString():
                return concat(*(self.describe(child) for child in ast.children))

            case TalonAction():
                # TODO: resolve self.*
                docstring = self.get_docstring(data.Action, name=ast.action_name.text)
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
            case _:
                raise TypeError(type(ast))
