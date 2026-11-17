"""Parse and evaluate the supported numeric LaTeX expression grammar."""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from ..triangles.right.planner import RightTrianglePlanError

_MIXED = re.compile(
    r"(?P<whole>\d+)\\frac\{(?P<numerator>\d+)\}\{(?P<denominator>\d+)\}$"
)
_FRACTION = re.compile(r"\\frac\{(?P<numerator>\d+)\}\{(?P<denominator>\d+)\}$")


class _ExpressionParser:
    """Parse the small, numeric-only LaTeX language used by this group."""

    def __init__(self, formula: str) -> None:
        self.formula = formula
        self.index = 0

    def parse(self) -> tuple[Any, ...]:
        node = self._sum()
        if self.index != len(self.formula):
            raise RightTrianglePlanError(
                "condition does not match a registered numeric rational expression"
            )
        return node

    def _sum(self) -> tuple[Any, ...]:
        node = self._product()
        while self._peek() in ("+", "-"):
            operation = self.formula[self.index]
            self.index += 1
            node = (operation, node, self._product())
        return node

    def _product(self) -> tuple[Any, ...]:
        node = self._unary()
        while True:
            if self.formula.startswith("\\cdot", self.index):
                self.index += len("\\cdot")
                node = ("\\cdot", node, self._unary())
            elif self.formula.startswith("\\colon", self.index):
                self.index += len("\\colon")
                node = ("\\colon", node, self._unary())
            else:
                return node

    def _unary(self) -> tuple[Any, ...]:
        if self._peek() == "-":
            self.index += 1
            return ("neg", self._unary())
        return self._primary()

    def _primary(self) -> tuple[Any, ...]:
        if self._peek() == "(":
            self.index += 1
            node = self._sum()
            if self._peek() != ")":
                raise RightTrianglePlanError(
                    "condition does not match a registered numeric rational expression"
                )
            self.index += 1
            return ("group", node)
        if self.formula.startswith("\\frac", self.index):
            self.index += len("\\frac")
            return (
                "frac",
                _ExpressionParser(self._braced()).parse(),
                _ExpressionParser(self._braced()).parse(),
            )
        mixed = re.match(r"\d+\\frac\{\d+\}\{\d+\}", self.formula[self.index :])
        if mixed is not None:
            raw = mixed.group(0)
            self.index += len(raw)
            return ("number", _number(raw), raw)
        match = re.match(r"\d+(?:\{,\}\d+)?", self.formula[self.index :])
        if match is None:
            raise RightTrianglePlanError(
                "condition does not match a registered numeric rational expression"
            )
        raw = match.group(0)
        self.index += len(raw)
        return ("number", Fraction(raw.replace("{,}", ".")), raw)

    def _braced(self) -> str:
        if self._peek() != "{":
            raise RightTrianglePlanError(
                "condition does not match a registered numeric rational expression"
            )
        start = self.index = self.index + 1
        depth = 1
        while self.index < len(self.formula) and depth:
            if self.formula[self.index] == "{":
                depth += 1
            elif self.formula[self.index] == "}":
                depth -= 1
            self.index += 1
        if depth:
            raise RightTrianglePlanError(
                "condition does not match a registered numeric rational expression"
            )
        return self.formula[start : self.index - 1]

    def _peek(self) -> str:
        return self.formula[self.index : self.index + 1]


def _expression_value(node: tuple[Any, ...]) -> Fraction:
    match node:
        case ("number", value, _):
            return value
        case ("group", child):
            return _expression_value(child)
        case ("neg", child):
            return -_expression_value(child)
        case ("frac", numerator, denominator):
            divisor = _expression_value(denominator)
            if not divisor:
                raise RightTrianglePlanError("division by zero")
            return _expression_value(numerator) / divisor
        case (operation, left, right) if operation in ("+", "-", "\\cdot", "\\colon"):
            left_value, right_value = _expression_value(left), _expression_value(right)
            if operation == "+":
                return left_value + right_value
            if operation == "-":
                return left_value - right_value
            if operation == "\\cdot":
                return left_value * right_value
            if not right_value:
                raise RightTrianglePlanError("division by zero")
            return left_value / right_value
    raise RightTrianglePlanError(
        "condition does not match a registered numeric rational expression"
    )


def _expression_latex(node: tuple[Any, ...], *, computed: bool = False) -> str:
    if computed and node[0] not in ("number",):
        return _fraction_latex(_expression_value(node))
    match node:
        case ("number", _, raw):
            return raw
        case ("group", child):
            return f"({_expression_latex(child)})"
        case ("neg", child):
            return f"-{_expression_latex(child)}"
        case ("frac", numerator, denominator):
            return f"\\frac{{{_expression_latex(numerator)}}}{{{_expression_latex(denominator)}}}"
        case (operation, left, right) if operation in ("+", "-", "\\cdot", "\\colon"):
            return f"{_expression_latex(left, computed=left[0] not in ('number', 'frac'))}{operation}{_expression_latex(right, computed=right[0] not in ('number', 'frac'))}"
    raise RightTrianglePlanError(
        "condition does not match a registered numeric rational expression"
    )


def _expression_steps(node: tuple[Any, ...]) -> list[str]:
    match node:
        case ("number", _, _):
            return []
        case ("group", child) | ("neg", child):
            return _expression_steps(child)
        case ("frac", numerator, denominator):
            steps = _expression_steps(numerator) + _expression_steps(denominator)
            if numerator[0] not in ("number", "frac") or denominator[0] not in (
                "number",
                "frac",
            ):
                steps.append(
                    f"{_expression_latex(node)}={_fraction_latex(_expression_value(node))}"
                )
            return steps
        case (operation, left, right) if operation in ("+", "-", "\\cdot", "\\colon"):
            steps = _expression_steps(left) + _expression_steps(right)
            steps.append(
                f"{_expression_latex(left, computed=left[0] not in ('number', 'frac'))}"
                f"{operation}{_expression_latex(right, computed=right[0] not in ('number', 'frac'))}"
                f"={_fraction_latex(_expression_value(node))}"
            )
            return steps
    raise RightTrianglePlanError(
        "condition does not match a registered numeric rational expression"
    )


def _number(value: str) -> Fraction:
    sign = -1 if value.startswith("-") else 1
    raw = value.removeprefix("-")
    if match := _MIXED.fullmatch(raw):
        result = Fraction(int(match["whole"])) + Fraction(
            int(match["numerator"]), int(match["denominator"])
        )
    elif match := _FRACTION.fullmatch(raw):
        result = Fraction(int(match["numerator"]), int(match["denominator"]))
    else:
        result = Fraction(raw.replace("{,}", "."))
    return sign * result


def _fraction_latex(value: Fraction) -> str:
    """Render a value explicitly as a fraction, including a denominator of one."""

    return f"{'-' if value < 0 else ''}\\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"
