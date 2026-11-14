"""Read positive exponential square roots and retain the remaining root as a node."""

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exponential_inequality_common_base import common_base, vector, weight
from .exponential_inequality_parser import ExponentialParser
from .exponential_inequality_quadratic import rational_gcd
from .logarithm_parser import Node
from .power_arithmetic import balanced
from .rational_exponential_input import leaves
from .rational_inequality_parser import X, polynomial


class ExponentialRootParser(ExponentialParser):
    def _nested(self, text):
        return ExponentialRootParser(text, self.denominators, self.depth + 1).parse()

    def _primary(self):
        if not self.text.startswith(r"\sqrt", self.index):
            return super()._primary()
        raw, self.index = balanced(self.text, self.index + 5)
        child = self._nested(raw)
        if child.kind == "exponential":
            base, exponent = child.children
            half = Node(exponent.value / 2, "")
            return Node(base.value**half.value, "", "exponential", (base, half))
        return Node(sp.sqrt(child.value), "", "root", (child,))


def coordinate(node):
    powers = leaves(node)
    if not powers:
        raise UnsupportedCondition("a positive exponential coordinate is required")
    base = common_base([p.children[0].value for p in powers])
    effective = [
        polynomial(
            sp.expand(weight(p.children[0].value, vector(base)) * p.children[1].value)
        )
        for p in powers
    ]
    if any(
        p.degree() != 1 or any(c.is_Rational is not True for c in p.all_coeffs())
        for p in effective
    ):
        raise UnsupportedCondition("rational affine exponential leaves are required")
    orientation = -1 if all(p.LC() < 0 for p in effective) else 1
    return base, orientation * rational_gcd([p.LC() for p in effective]) * X


def project(node, base, exponent):
    if node.kind == "exponential":
        b, g = (c.value for c in node.children)
        effective = sp.expand(weight(b, vector(base)) * g)
        degree = sp.cancel(sp.diff(effective, X) / sp.diff(exponent, X))
        offset = sp.cancel(effective - degree * exponent)
        if (
            degree.is_Integer is not True
            or abs(degree) > 4
            or offset.is_Rational is not True
            or abs(offset) > 40
            or offset.q > 2
        ):
            raise UnsupportedCondition(
                "small exponential powers with rational or quadratic coefficients are required"
            )
        return polynomial(base**offset * X**degree).as_expr()
    if node.kind == "negative":
        return -project(node.children[0], base, exponent)
    if node.kind in ("add", "subtract", "multiply", "divide", "power"):
        a, b = (project(c, base, exponent) for c in node.children)
        return {
            "add": lambda: a + b,
            "subtract": lambda: a - b,
            "multiply": lambda: a * b,
            "divide": lambda: a / b,
            "power": lambda: a**b,
        }[node.kind]()
    if node.value.free_symbols or node.kind == "root":
        raise UnsupportedCondition(
            "only exponential leaves and scalar arithmetic are supported outside the single root"
        )
    return node.value
