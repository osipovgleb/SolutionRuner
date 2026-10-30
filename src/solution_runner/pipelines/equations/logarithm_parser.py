"""Typed arithmetic grammar for numeric logarithms, roots and powers."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from . import logarithm_arithmetic as arithmetic
from .power_arithmetic import balanced, clean, rational


@dataclass
class Node:
    value: sp.Expr
    text: str
    kind: str = "scalar"
    children: tuple = ()


def combined(kind, left, right):
    a, b = left.value, right.value
    if kind == "divide":
        arithmetic.nonzero(b)
    value = arithmetic.checked(
        {
            "add": lambda: a + b,
            "subtract": lambda: a - b,
            "multiply": lambda: a * b,
            "divide": lambda: a / b,
        }[kind]()
    )
    text = (
        rf"\frac{{{left.text}}}{{{right.text}}}"
        if kind == "divide"
        else "("
        + left.text
        + ")"
        + {"add": "+", "subtract": "-", "multiply": r"\cdot"}[kind]
        + "("
        + right.text
        + ")"
    )
    return Node(value, text, kind, (left, right))


class LogarithmParser:
    def __init__(self, text, depth=0):
        text = re.sub(r"\\log_([2-9])(?=\s)", r"\\log_{\1}", text)
        self.text = clean(text)
        self.index = 0
        self.depth = depth
        if len(self.text) > 1500 or depth > 20:
            raise UnsupportedCondition("the logarithm syntax exceeds supported bounds")

    def parse(self):
        value = self._sum()
        if self.index != len(self.text):
            raise UnsupportedCondition("unsupported complete logarithm expression")
        return value

    def _nested(self, text):
        return LogarithmParser(text, self.depth + 1).parse()

    _combine = staticmethod(combined)

    def _sum(self):
        value = self._product()
        while self.text[self.index : self.index + 1] in ("+", "-"):
            operator = self.text[self.index]
            self.index += 1
            value = self._combine(
                "add" if operator == "+" else "subtract", value, self._product()
            )
        return value

    def _product(self):
        value = self._factor()
        while self.index < len(self.text):
            kind = "multiply"
            for operator in (r"\cdot", r"\times", r"\colon", r"\div", "*", "/"):
                if self.text.startswith(operator, self.index):
                    self.index += len(operator)
                    kind = (
                        "divide"
                        if operator in (r"\colon", r"\div", "/")
                        else "multiply"
                    )
                    break
            else:
                if not (
                    self.text[self.index] == "("
                    or self.text.startswith((r"\log", r"\sqrt"), self.index)
                ):
                    break
            value = self._combine(kind, value, self._factor())
        return value

    def _exponent(self):
        self.index += 1
        if self.text[self.index : self.index + 1] == "{":
            text, self.index = balanced(self.text, self.index)
            return self._nested(text)
        match = re.match(r"[+-]?\d", self.text[self.index :])
        if not match:
            raise UnsupportedCondition("an explicit logarithmic exponent is required")
        self.index += match.end()
        return self._nested(match.group())

    def _factor(self):
        token = self.text[self.index : self.index + 1]
        if token in ("+", "-"):
            self.index += 1
            other = self._factor()
            return (
                other
                if token == "+"
                else Node(-other.value, "-(" + other.text + ")", "negative", (other,))
            )
        value = self._primary()
        if self.text[self.index : self.index + 1] == "^":
            exponent = self._exponent()
            result = arithmetic.power(value.value, exponent.value)
            value = Node(
                result,
                "(" + value.text + ")^{" + exponent.text + "}",
                "power",
                (value, exponent),
            )
        return value

    def _log(self):
        self.index += 5
        if self.text[self.index : self.index + 1] == "{":
            text, self.index = balanced(self.text, self.index)
        elif self.text[self.index : self.index + 1] in "23456789" and self.index < len(
            self.text
        ):
            text = self.text[self.index]
            self.index += 1
        else:
            raise UnsupportedCondition("an unambiguous logarithm base is required")
        base = self._nested(text)
        exponent = (
            self._exponent() if self.text[self.index : self.index + 1] == "^" else None
        )
        argument = self._factor()
        value = arithmetic.log_ratio(base.value, argument.value)
        result = Node(
            value, rf"\log_{{{base.text}}}({argument.text})", "log", (base, argument)
        )
        if exponent:
            result = Node(
                arithmetic.power(result.value, exponent.value),
                "(" + result.text + ")^{" + exponent.text + "}",
                "power",
                (result, exponent),
            )
        return result

    def _primary(self):
        if self.text.startswith(r"\log_", self.index):
            return self._log()
        token = self.text[self.index : self.index + 1]
        if token == "(":
            text, self.index = balanced(self.text, self.index, "(", ")")
            return self._nested(text)
        if self.text.startswith(r"\frac", self.index):
            self.index += 5
            a, self.index = balanced(self.text, self.index)
            b, self.index = balanced(self.text, self.index)
            return self._combine("divide", self._nested(a), self._nested(b))
        if self.text.startswith(r"\sqrt", self.index):
            self.index += 5
            degree = 2
            if self.text[self.index : self.index + 1] == "[":
                text, self.index = balanced(self.text, self.index, "[", "]")
                if not re.fullmatch(r"\d{1,3}", text) or not 2 <= int(text) <= 100:
                    raise UnsupportedCondition("unsupported logarithm root index")
                degree = int(text)
            text, self.index = balanced(self.text, self.index)
            inside = self._nested(text)
            value = arithmetic.power(inside.value, sp.Rational(1, degree))
            return Node(value, rf"\sqrt[{degree}]{{{inside.text}}}", "root", (inside,))
        match = re.match(r"(?:0|[1-9]\d*)(?:\.\d+)?", self.text[self.index :])
        if not match:
            raise UnsupportedCondition("unsupported logarithm expression operand")
        self.index += match.end()
        value = rational(match.group())
        text = match.group().replace(".", "{,}")
        if self.text.startswith(r"\frac", self.index):
            fraction = self._primary()
            if (
                value.is_Integer is not True
                or fraction.value.is_Rational is not True
                or not 0 < fraction.value < 1
            ):
                raise UnsupportedCondition(
                    "a mixed numeral requires a proper fractional part"
                )
            value += fraction.value
            text += fraction.text
        return Node(value, text)
