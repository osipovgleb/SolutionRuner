"""Read typed polynomial moduli without losing any original rational denominator."""

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_parser import Node
from .power_arithmetic import clean
from .radical_inequality_parser import RadicalParser
from .rational_inequality_parser import RationalParser, X, polynomial


class AbsoluteParser(RadicalParser):
    def __init__(self, text, denominators=None, depth=0, values=None):
        pieces = clean(text).split("|")
        for i in range(0, len(pieces) - 1, 2):
            if pieces[i][-1:] and pieces[i][-1:] in "0123456789x)":
                pieces[i] += "*"
        super().__init__("|".join(pieces), denominators, depth, radicands=values)
        # The inherited checker treats these as bounded typed symbols, not root domains.
        self.absolute_values = self.radicands

    def _nested(self, text):
        return AbsoluteParser(
            text, self.denominators, self.depth + 1, self.absolute_values
        ).parse()

    def _primary(self):
        if self.text[self.index : self.index + 1] != "|":
            return RationalParser._primary(self)
        end = self.text.find("|", self.index + 1)
        if end < 0:
            raise UnsupportedCondition("a complete nonnested modulus is required")
        raw = self.text[self.index + 1 : end]
        self.index = end + 1
        value = RationalParser(raw, self.denominators, self.depth + 1).parse().value
        if polynomial(value).degree() > 2:
            raise UnsupportedCondition(
                "at most quadratic polynomial modulus arguments are reviewed"
            )
        if not value.has(X):
            return Node(sp.Abs(value), "", "scalar")
        value = sp.expand(value)
        symbol = next((s for s, p in self.absolute_values.items() if p == value), None)
        if symbol is None:
            if len(self.absolute_values) >= 3:
                raise UnsupportedCondition(
                    "at most three polynomial modulus arguments are supported"
                )
            symbol = sp.Dummy("absolute", real=True)
            self.absolute_values[symbol] = value
        return Node(symbol, "", "absolute")
