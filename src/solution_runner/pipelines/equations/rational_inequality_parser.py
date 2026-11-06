"""Closed rational grammar retaining denominators before symbolic cancellation."""

import re

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_parser import LogarithmParser, Node
from .power_arithmetic import balanced, rational

X = sp.Symbol("x", real=True)


def polynomial(value):
    if not value.is_polynomial(X) or value.free_symbols - {X}:
        raise UnsupportedCondition("a rational polynomial in x is required")
    result = sp.Poly(value, X)
    coefficients = result.all_coeffs()
    if (
        result.degree() > 8
        or sp.count_ops(value) > 150
        or len(value.atoms(sp.Pow)) > 20
        or len({p.base for p in value.atoms(sp.Pow) if p.exp == sp.Rational(1, 2)}) > 2
        or any(
            sp.count_ops(c) > 40
            or c.is_algebraic is not True
            or c.is_real is not True
            or any(max(abs(n.p), n.q) > 10**12 for n in c.atoms(sp.Rational))
            or len(c.atoms(sp.Pow)) > 4
            for c in coefficients
        )
    ):
        raise UnsupportedCondition("the polynomial exceeds the reviewed exact bounds")
    return result


def checked(value):
    numerator, denominator = sp.fraction(sp.cancel(value))
    polynomial(numerator)
    polynomial(denominator)
    return value


class RationalParser(LogarithmParser):
    def __init__(self, text, denominators=None, depth=0):
        super().__init__(text, depth)
        if sum(self.text.count(token) for token in "+-*/^(") > 100:
            raise UnsupportedCondition("too many rational arithmetic operations")
        self.denominators = [] if denominators is None else denominators

    def _nested(self, text):
        return RationalParser(text, self.denominators, self.depth + 1).parse()

    def _combine(self, kind, left, right):
        a, b = left.value, right.value
        if kind == "divide":
            if b == 0:
                raise UnsupportedCondition("division by zero in the original condition")
            self.denominators.append(b)
        value = {
            "add": lambda: a + b,
            "subtract": lambda: a - b,
            "multiply": lambda: a * b,
            "divide": lambda: a / b,
        }[kind]()
        return Node(checked(value), "", kind, (left, right))

    def _product(self):
        value = self._factor()
        while self.index < len(self.text):
            for operator in (r"\cdot", r"\times", r"\colon", r"\div", "*", "/"):
                if self.text.startswith(operator, self.index):
                    self.index += len(operator)
                    break
            else:
                if self.text[self.index] not in "(x" and not self.text.startswith(
                    (r"\frac", r"\sqrt"), self.index
                ):
                    break
                operator = "*"
            kind = "divide" if operator in (r"\colon", r"\div", "/") else "multiply"
            value = self._combine(kind, value, self._factor())
        return value

    def _factor(self):
        token = self.text[self.index : self.index + 1]
        if token in ("+", "-"):
            self.index += 1
            other = self._factor()
            return (
                other if token == "+" else Node(-other.value, "", "negative", (other,))
            )
        value = self._primary()
        if self.text[self.index : self.index + 1] == "^":
            exponent = self._exponent()
            if exponent.value.is_Integer is not True or not -8 <= exponent.value <= 8:
                raise UnsupportedCondition("a small integer rational power is required")
            if exponent.value <= 0:
                if value.value == 0:
                    raise UnsupportedCondition("zero cannot have a nonpositive power")
                self.denominators.append(value.value)
            value = Node(
                checked(value.value**exponent.value), "", "power", (value, exponent)
            )
        return value

    def _primary(self):
        token = self.text[self.index : self.index + 1]
        if token == "x":
            self.index += 1
            return Node(X, "x", "variable")
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
            raw, self.index = balanced(self.text, self.index)
            if not re.fullmatch(r"\d{1,7}", raw) or int(raw) > 10**6:
                raise UnsupportedCondition(
                    "a bounded constant integer square root is required"
                )
            return Node(sp.sqrt(int(raw)), r"\sqrt{" + raw + "}", "scalar")
        match = re.match(r"(?:0|[1-9]\d*)(?:\.\d+)?", self.text[self.index :])
        if match is None:
            raise UnsupportedCondition("unsupported rational expression operand")
        self.index += match.end()
        return Node(rational(match.group()), match.group())
