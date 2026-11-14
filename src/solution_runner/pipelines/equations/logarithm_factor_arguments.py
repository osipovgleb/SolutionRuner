"""Read bounded factored rational arguments while retaining their original zeros."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .laurent_arithmetic import symbolic
from .laurent_parser import LaurentParser
from .power_arithmetic import balanced, clean
from .rational_inequality_parser import X
from .rational_inequality_roots import ordered, real_roots
from .rational_substitution_preimages import comparison


def read_polynomial(text):
    text = re.sub(r"x(?=\()", lambda _: r"x\cdot", text)
    parser = LaurentParser(text)
    value = symbolic(parser.parse())
    if value.free_symbols - {X} or not value.is_polynomial(X) or parser.nonzero - {"x"}:
        raise UnsupportedCondition("one rational polynomial in x is required")
    p = sp.Poly(value, X)
    if (
        p.is_zero
        or p.degree() > 20
        or any(max(abs(c.p), c.q) > 10**12 for c in p.all_coeffs())
    ):
        raise UnsupportedCondition(
            "the factored argument exceeds the reviewed polynomial bounds"
        )
    return value, ({sp.S.Zero} if parser.nonzero else set())


@dataclass(frozen=True)
class FactorArgument:
    raw: str
    numerator: sp.Expr
    denominator: sp.Expr
    coefficient: sp.Expr
    factors: tuple
    excluded: tuple
    domain: object

    @property
    def value(self):
        return sp.cancel(self.numerator / self.denominator)


def read_argument(raw):
    text = clean(raw)
    while text.startswith("("):
        inside, end = balanced(text, 0, "(", ")")
        if end != len(text):
            break
        text = inside
    if text.startswith(r"\frac"):
        n, index = balanced(text, 5)
        d, index = balanced(text, index)
        if index != len(text):
            raise UnsupportedCondition("one complete polynomial fraction is required")
    else:
        n, d = text, "1"
    numerator, excluded = read_polynomial(n)
    denominator, extra = read_polynomial(d)
    excluded.update(extra)
    factors = {}
    for value, sign in ((numerator, 1), (denominator, -1)):
        parts = sp.factor_list(value, X)[1]
        if len(parts) > 8:
            raise UnsupportedCondition("too many distinct argument factors")
        for factor, degree in parts:
            p = sp.Poly(factor, X)
            if p.degree() not in (1, 2):
                raise UnsupportedCondition(
                    "each exact argument factor must be linear or quadratic"
                )
            factor = p.monic().as_expr()
            excluded.update(real_roots(factor))
            factors[factor] = factors.get(factor, 0) + sign * degree
    coefficient = sp.Poly(numerator, X).LC() / sp.Poly(denominator, X).LC()
    odd = sp.prod(f for f, k in factors.items() if k % 2)
    domain = comparison(
        (1 if coefficient > 0 else -1) * odd, ">"
    ).solution - sp.FiniteSet(*excluded)
    return FactorArgument(
        raw,
        numerator,
        denominator,
        coefficient,
        tuple(
            sorted(
                ((f, k) for f, k in factors.items() if k),
                key=lambda v: sp.default_sort_key(v[0]),
            )
        ),
        ordered(excluded),
        domain,
    )
