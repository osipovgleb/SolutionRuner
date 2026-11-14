"""Read rational expressions in typed polynomial roots without losing poles."""

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_parser import Node
from .power_arithmetic import balanced
from .rational_inequality_parser import RationalParser, X, polynomial


class RadicalParser(RationalParser):
    def __init__(self, text, denominators=None, depth=0, radicands=None):
        super().__init__(text, denominators, depth)
        self.radicands = {} if radicands is None else radicands

    def _nested(self, text):
        return RadicalParser(
            text, self.denominators, self.depth + 1, self.radicands
        ).parse()

    def _checked(self, value):
        symbols = (X, *self.radicands)
        if value.free_symbols - set(symbols) or sp.count_ops(value) > 150:
            raise UnsupportedCondition("unsupported polynomial-root arithmetic")
        for part in sp.fraction(sp.cancel(value)):
            if not part.is_polynomial(*symbols):
                raise UnsupportedCondition(
                    "rational arithmetic in typed roots is required"
                )
            poly = sp.Poly(part, *symbols)
            if poly.total_degree() > 8:
                raise UnsupportedCondition("the polynomial-root degree exceeds bounds")
            for coefficient in poly.coeffs():
                polynomial(coefficient)
        return value

    def _primary(self):
        if not self.text.startswith(r"\sqrt", self.index):
            return super()._primary()
        raw, self.index = balanced(self.text, self.index + 5)
        reader = RationalParser(raw, self.denominators, self.depth + 1)
        value = reader.parse().value
        if polynomial(value).degree() > 3:
            raise UnsupportedCondition(
                "at most cubic polynomial radicands are supported"
            )
        if not value.has(X):
            if value.is_nonnegative is not True:
                raise UnsupportedCondition("a real constant root is required")
            return Node(sp.sqrt(value), r"\sqrt{" + raw + "}", "scalar")
        canonical = sp.expand(value)
        symbol = next(
            (s for s, radicand in self.radicands.items() if radicand == canonical), None
        )
        if symbol is None:
            if len(self.radicands) >= 3:
                raise UnsupportedCondition(
                    "at most three polynomial roots are supported"
                )
            symbol = sp.Dummy("root", real=True)
            self.radicands[symbol] = canonical
        return Node(symbol, r"\sqrt{" + raw + "}", "root")
