"""Retain the source grouping, exact perfect square and interval rationalization."""

import sympy as sp

from ..probability.common import line
from .exponential_inequality_proof import power
from .exponential_inequality_reduction_proof import sum_terms
from .rational_exponential_figures import multiplicity
from .rational_inequality_parser import X, polynomial
from .rational_inequality_proof import RELATION, domain, interval_proof, normalized


def numerator_steps(a):
    double = next(z for z in a.stage.zeros if multiplicity(a.numerator, z) == 2)
    factor = X - double
    q, r = sp.div(a.numerator, factor, X)
    if r != 0:
        raise ValueError("the certified numerator factor must divide exactly")
    grouped = sum_terms(
        [
            (
                c,
                (sp.latex(X**k) if k else "")
                + r"\left("
                + sp.latex(factor)
                + r"\right)",
            )
            for (k,), c in polynomial(q).terms()
        ]
    )
    return line(sp.latex(a.numerator) + "=" + grouped) + line(
        r"\left("
        + sp.latex(factor)
        + r"\right)\left("
        + sp.latex(q)
        + r"\right)"
        + "="
        + sp.latex(sp.factor(a.numerator))
    )


def render(a, image=""):
    actual = power(a.base, a.exponent)
    actual_denominator = sum_terms(
        [
            (c, power(a.base, k * a.exponent) if k else "")
            for k, c in reversed(a.coefficients)
        ]
    )
    square = (
        (sp.latex(a.scalar) + r"\cdot " if a.scalar != 1 else "")
        + r"\left("
        + actual
        + "-"
        + sp.latex(a.root)
        + r"\right)^2"
    )
    html = (
        "<p>Разложим числитель на множители, группируя слагаемые:</p>"
        + numerator_steps(a)
    )
    html += "<p>Знаменатель представим в виде полного квадрата:</p>"
    html += line(actual_denominator + "=" + square)
    html += domain(a.stage)
    html += "<p>Рационализируем разность степеней. При основании больше единицы она имеет тот же знак и те же нули, что разность показателей. Квадраты сохраняют исключённые точки знаменателя:</p>"
    html += line(sp.latex(a.root) + "=" + power(a.base, a.level))
    if a.scalar != 1:
        html += "<p>Положительный числовой множитель знаменателя не влияет на знак дроби.</p>"
    factored = sp.latex(sp.factor(a.numerator))
    rationalized = sp.latex((a.exponent - a.level) ** 2)
    html += line(
        r"\frac{" + factored + "}{" + square + "}" + RELATION[a.operator] + "0"
    )
    html += line(
        r"\frac{" + factored + "}{" + rationalized + "}" + RELATION[a.operator] + "0"
    )
    d = sp.fraction(a.stage.original)[1]
    html += line(
        r"\frac{"
        + factored
        + "}{"
        + sp.latex(sp.factor(d, extension=a.stage.poles or True))
        + "}"
        + RELATION[a.operator]
        + "0"
    )
    html += "<p>Двойные нули не меняют знак, но включаются при нестрогом сравнении; двойные полюсы исключены.</p>"
    if sp.cancel(a.stage.original / a.stage.expression) != 1:
        html += normalized(a.stage, already_factored=True)
    return html + interval_proof(a.stage, image)
