"""Reduce a reviewed symmetric cubic using t = sin(x) + cos(x)."""

import re
from dataclasses import dataclass, replace

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S, T

V = sp.Symbol("t", real=True)


@dataclass(frozen=True)
class SumReduction:
    polynomial: sp.Expr
    variable: str
    nonpositive: bool


def style(parent_html):
    soup = BeautifulSoup(parent_html, "html.parser")
    text = " ".join(soup.get_text(" ").replace("\xad", "").lower().split())
    nonpositive = "оба слагаемых не больше" in text
    names = []
    for node in soup.select("[data-inline-latex]"):
        formula = "".join(node["data-inline-latex"].split())
        match = re.fullmatch(r"([ty])=\\(?:sinx\+\\cosx|cosx\+\\sinx)", formula)
        if match:
            names.append(match[1])
    if len(set(names)) > 1:
        raise UnsupportedCondition("one combined-function substitution is required")
    return (names[0] if names else "t"), nonpositive, bool(names) or nonpositive


def prepare(compiled, parent_html, translation):
    raw = compiled.raw
    if (
        translation
        or compiled.scale != 1
        or compiled.poles
        or raw.free_symbols != {S, C}
        or not raw.is_polynomial(S, C)
        or sp.Poly(raw, S, C).total_degree() != 3
    ):
        return None
    variable, nonpositive, reviewed = style(parent_html)
    if not reviewed:
        return None
    symmetric, remainder, pairs = sp.symmetrize(raw, [S, C], formal=True)
    if remainder != 0:
        raise UnsupportedCondition("the combined-function polynomial must be symmetric")
    polynomial = sp.expand(
        symmetric.subs(
            {pairs[0][0]: V, pairs[1][0]: (V * V - 1) / 2}, simultaneous=True
        )
    )
    if (
        sp.degree(polynomial, V) != 3
        or sp.rem(raw - polynomial.subs(V, S + C), S * S + C * C - 1, S) != 0
    ):
        raise UnsupportedCondition(
            "the symmetric substitution must preserve the unit-circle equation"
        )
    if nonpositive:
        ratio = sp.cancel(polynomial / ((V - 1) ** 2 * (V + 2)))
        if ratio.free_symbols or not ratio:
            raise UnsupportedCondition(
                "the nonpositive-summand method requires the reviewed cubic equality"
            )
    return replace(compiled, symmetric=SumReduction(polynomial, variable, nonpositive))


def branches(reduction, parent_html):
    from .exam_trigonometric import Branch
    from .exam_trigonometric_linear_phase import branch, notation
    from .exam_trigonometric_ratios import linear_branch

    result = []
    for value in roots(reduction.polynomial.subs(V, X)):
        expression = S + C - value
        if compare(value, -sp.sqrt(2)) < 0 or compare(value, sp.sqrt(2)) > 0:
            result.append(
                Branch(T, sp.S.One, (), (), (), original=expression, impossible=True)
            )
        else:
            found = linear_branch(expression) or branch(expression)
            if found is None:
                raise UnsupportedCondition(
                    "the combined-function level needs a reviewed exact angle"
                )
            result.append(found)
    return notation(tuple(result), parent_html)
