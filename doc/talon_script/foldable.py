from abc import *
from typing import *
from talon import actions
from talon.scripting.context import *
from talon.scripting.talon_script import *
from talon.scripting.types import *
import re


class FoldableTalonScript(ABC):

    def fold_command(self, command: CommandImpl):
        return self.fold_script(command.target)

    def fold_script(self, talon_script: TalonScript):
        return tuple(self.fold_expr(stmt) for stmt in talon_script.lines)

    def fold_expr(self, expr: Expr):
        """"""

        # Comments
        if isinstance(expr, Comment):
            return self.comment(expr.text)

        # Operators
        if isinstance(expr, ExprAdd):
            return self.operator_add(expr.v1, expr.op, expr.v2)
        if isinstance(expr, ExprSub):
            return self.operator_sub(expr.v1, expr.op, expr.v2)
        if isinstance(expr, ExprMul):
            return self.operator_mul(expr.v1, expr.op, expr.v2)
        if isinstance(expr, ExprDiv):
            return self.operator(expr.v1, expr.op, expr.v2)
        if isinstance(expr, ExprMod):
            return self.operator(expr.v1, expr.op, expr.v2)
        if isinstance(expr, ExprOr):
            return self.operator(expr.v1, expr.op, expr.v2)
        if isinstance(expr, ExprOp):
            return self.operator(expr.v1, expr.op, expr.v2)

        # Values
        if isinstance(expr, KeyValue):
            return self.key_value(expr.value)
        if isinstance(expr, StringValue):
            return self.string_value(expr.value)
        if isinstance(expr, FormatStringValue):
            return self.format_string(expr.value, expr.parts)
        if isinstance(expr, NumberValue):
            return self.number_value(expr.value)
        if isinstance(expr, Value):
            return self.value(expr.value)

        # Variables
        if isinstance(expr, Variable):
            return self.variable(expr.name)

        # Statements
        if isinstance(expr, KeyStatement):
            return self.key_statement(expr.keys)
        if isinstance(expr, Sleep):
            return self.sleep(expr.args)
        if isinstance(expr, Repeat):
            return self.repeat(expr.value)
        if isinstance(expr, Action):
            return self.action(expr.name, expr.args)
        if isinstance(expr, Assignment):
            return self.assignment(expr.var, expr.expr)

        raise ValueError(f"Unexpected value {expr} of type {type(expr)}")

    def comment(self, text):
        """"""

    def operator_add(self, v1: Expr, op: str, v2: Expr):
        """"""
        return self.operator(v1, op, v2)

    def operator_sub(self, v1: Expr, op: str, v2: Expr):
        """"""
        return self.operator(v1, op, v2)

    def operator_mul(self, v1: Expr, op: str, v2: Expr):
        """"""
        return self.operator(v1, op, v2)

    def operator_div(self, v1: Expr, op: str, v2: Expr):
        """"""
        return self.operator(v1, op, v2)

    def operator_mod(self, v1: Expr, op: str, v2: Expr):
        """"""
        return self.operator(v1, op, v2)

    def operator_or(self, v1: Expr, op: str, v2: Expr):
        """"""
        return self.operator(v1, op, v2)

    def operator(self, v1: Expr, op: str, v2: Expr):
        """"""

    def key_value(self, value: str):
        """"""
        return self.string_value(value)

    def string_value(self, value: str):
        """"""
        return self.value(value)

    def format_string(self, value: str, parts: Sequence[Expr]):
        """"""
        return self.value(value)

    def number_value(self, value: Union[int, float]):
        """"""
        return self.value(value)

    def value(self, value: Any):
        """"""

    def variable(self, name: str):
        """"""

    # Statements

    def action(self, name: str, args: Sequence[Expr]):
        """"""

    def key_statement(self, keys: Sequence[StringValue]):
        """"""
        return self.action("key", keys)

    def sleep(self, args: Sequence[Value]):
        """"""
        return self.action("sleep", args)

    def repeat(self, value: Value):
        """"""
        return self.action("repeat", (value,))

    def assignment(self, var: str, expr: Expr):
        """"""
