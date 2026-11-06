"""Bounded typed arithmetic with positive rational bases and exact rational exponents."""

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_parser import Node
from .rational_inequality_parser import RationalParser, X, checked, polynomial


def bounded(value):
    if (
        value.free_symbols - {X}
        or value.has(sp.zoo, sp.nan, sp.oo, -sp.oo)
        or sp.count_ops(value) > 200
        or len(value.atoms(sp.Pow)) > 24
        or any(max(abs(n.p), n.q) > 10**12 for n in value.atoms(sp.Rational))
    ):
        raise UnsupportedCondition(
            "the exponential expression exceeds exact arithmetic bounds"
        )
    variable_powers = [p for p in value.atoms(sp.Pow) if p.exp.has(X)]
    if not variable_powers:
        checked(value)
    return value


class ExponentialParser(RationalParser):
    def _nested(self, text):
        return ExponentialParser(text, self.denominators, self.depth + 1).parse()

    def _exponent(self):
        if self.text[self.index + 1 : self.index + 2] == "x":
            self.index += 2
            return Node(X, "x", "variable")
        return super()._exponent()

    def _combine(self, kind, left, right):
        a, b = left.value, right.value
        if kind == "divide":
            if b == 0:
                raise UnsupportedCondition(
                    "division by zero in the exponential condition"
                )
            self.denominators.append(b)
        value = {
            "add": lambda: a + b,
            "subtract": lambda: a - b,
            "multiply": lambda: a * b,
            "divide": lambda: a / b,
        }[kind]()
        return Node(bounded(value), "", kind, (left, right))

    def _factor(self):
        token = self.text[self.index : self.index + 1]
        if token in ("+", "-"):
            self.index += 1
            other = self._factor()
            return (
                other if token == "+" else Node(-other.value, "", "negative", (other,))
            )
        base = self._primary()
        if self.text[self.index : self.index + 1] != "^":
            return base
        exponent = self._exponent()
        a, b = base.value, exponent.value
        if b.free_symbols:
            if a.is_Rational is not True or a <= 0 or a == 1 or max(a.p, a.q) > 10**6:
                raise UnsupportedCondition(
                    "a variable exponent needs a bounded positive rational base other than one"
                )
            numerator, denominator = sp.fraction(sp.cancel(b))
            if (
                polynomial(numerator).degree() > 2
                or polynomial(denominator).degree() > 2
                or any(
                    c.is_Rational is not True
                    for p in (numerator, denominator)
                    for c in polynomial(p).all_coeffs()
                )
            ):
                raise UnsupportedCondition(
                    "the exponent must be a bounded rational expression in x"
                )
            kind = "exponential"
        else:
            if b.is_Integer is not True or abs(b) > 8:
                raise UnsupportedCondition(
                    "an ordinary arithmetic power needs a small integer exponent"
                )
            if b <= 0:
                if a == 0:
                    raise UnsupportedCondition("zero cannot have a nonpositive power")
                self.denominators.append(a)
            kind = "power"
        return Node(bounded(a**b), "", kind, (base, exponent))
