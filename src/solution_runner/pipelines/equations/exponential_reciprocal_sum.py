"""Reduce symmetric Laurent powers through the parent's reciprocal-sum substitution."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exam_exponential import back_substitute
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_quadratic import inverse, normalize_powers, read_power_sum
from .exponential_inequality_reduction_proof import sum_terms
from .rational_inequality import analyze as rational
from .rational_inequality import set_latex
from .rational_inequality_parser import X
from .rational_inequality_proof import RELATION
from .rational_substitution_preimages import branches, comparison


@dataclass(frozen=True)
class ReciprocalSum:
    base: sp.Expr
    exponent: sp.Expr
    coefficients: tuple
    operator: str
    stage: object
    reachable: object
    branches: tuple
    positive: object
    back: tuple
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def analyze(formula):
    operator, _, powers, constant = read_power_sum(formula)
    base, exponent, coefficients = normalize_powers(powers, constant)
    if (
        set(coefficients) - {-2, -1, 0, 1, 2}
        or coefficients.get(2, 0) == 0
        or coefficients.get(2) != coefficients.get(-2)
        or coefficients.get(1, 0) != coefficients.get(-1, 0)
    ):
        raise UnsupportedCondition("the reciprocal-sum coefficients must be symmetric")
    a, b, c = coefficients[2], coefficients.get(1, 0), coefficients.get(0, 0)
    stage = rational(sp.latex(a * (X**2 - 2) + b * X + c) + RELATION[operator] + "0")
    reachable = sp.Intersection(stage.solution, sp.Interval(2, sp.oo))
    parts = branches(
        reachable,
        sp.Interval.open(0, sp.oo),
        lambda t, op: comparison(X + 1 / X - t, op),
    )
    positive = sp.Union(*(p.solution for p in parts))
    endpoints = tuple(v for v in positive.boundary if v.is_finite and v > 0)
    _, back = back_substitute(base, exponent, endpoints)
    mapping = {t: points[0] for t, _, points in back}
    solution = inverse(positive, mapping, sp.Poly(exponent, X).nth(1) > 0)
    return ReciprocalSum(
        base,
        exponent,
        tuple(sorted(coefficients.items())),
        operator,
        stage,
        reachable,
        parts,
        positive,
        tuple(back),
        solution,
    )


def render(a):
    power = sp.latex(a.base) + "^{" + sp.latex(a.exponent) + "}"
    reciprocal = r"\frac{1}{" + power + "}"
    total = power + "+" + reciprocal
    coeff = dict(a.coefficients)
    square_sum = sp.latex(a.base) + "^{" + sp.latex(2 * a.exponent) + "}"
    pair = square_sum + r"+\frac{1}{" + square_sum + "}"
    html = "<p>Перепишем неравенство, объединив взаимно обратные степени, и введём замену:</p>"
    grouped = sum_terms(
        [
            (sp.sign(c), ("" if abs(c) == 1 else sp.latex(abs(c))) + "(" + value + ")")
            for c, value in ((coeff[2], pair), (coeff.get(1, 0), total))
            if c != 0
        ]
    )
    html += line(grouped + RELATION[a.operator] + sp.latex(-coeff.get(0, 0)))
    html += line("t=" + total)
    html += "<p>Квадрат суммы отличается от суммы квадратов на два. Кроме того, сумма положительного числа и обратного к нему не меньше двух:</p>"
    html += line("t^2=" + pair + "+2,\\qquad " + pair + "=t^2-2")
    html += line(total + r"\ge 2,\qquad t\ge 2")
    html += "<p>После замены решаем квадратное неравенство и учитываем область значений новой переменной:</p>"
    html += line(
        sp.latex(a.stage.original).replace("x", "t") + RELATION[a.operator] + "0"
    )
    html += line(alternatives("t", a.stage.solution))
    html += line(alternatives("t", a.reachable))
    if a.reachable == sp.FiniteSet(2):
        html += "<p>Равенство достигается, только когда положительное число равно обратному к нему:</p>"
        html += line(total + "=2")
        html += line(
            "(" + power + r"-1)^2=0\quad\Longleftrightarrow\quad " + power + "=1"
        )
    elif a.positive != sp.EmptySet:
        html += "<p>Возвращаемся к положительной степени, сохраняя открытые и закрытые границы:</p>"
        html += line(alternatives(power, a.positive))
    html += "<p>Возвращаясь к исходной переменной, получаем:</p>"
    return html + line(alternatives("x", a.solution))
