"""Certify equality at the upper bound of a two-term trigonometric sum."""

import sympy as sp
from bs4 import BeautifulSoup
from sympy.simplify.fu import TR8

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S, table
from .exam_trigonometric_sum_identities import X, literal


def reviewed(html):
    text = BeautifulSoup(html, "html.parser").get_text(" ").replace("\xad", "").lower()
    return "может достигаться только" in text and "решим систему уравнений" in text


def compile_extremum(formula):
    from .exam_trigonometric_methods import Equation

    polynomial, _atoms, functions = literal(formula)
    raw = polynomial.xreplace(functions)
    reduced = sp.expand(TR8(raw))
    terms = sorted(reduced.atoms(sp.sin, sp.cos), key=sp.default_sort_key)
    if len(terms) != 2 or any(
        sp.cancel(f.args[0] / X).is_Integer is not True
        or not 1 <= sp.cancel(f.args[0] / X) <= 12
        for f in terms
    ):
        raise UnsupportedCondition(
            "two bounded unshifted angle functions are required for the extremum proof"
        )
    constant = reduced.xreplace(dict.fromkeys(terms, 0))
    weights = [reduced.coeff(f) for f in terms]
    if (
        constant.free_symbols
        or any(w.free_symbols or w.is_real is not True or w == 0 for w in weights)
        or sp.expand(reduced - constant - sum(w * f for w, f in zip(weights, terms)))
        != 0
        or sp.simplify(-constant - sum(abs(w) for w in weights)) != 0
    ):
        raise UnsupportedCondition(
            "the sum must equal the sum of its individual upper bounds"
        )
    constraints = tuple((f, sp.sign(w)) for f, w in zip(terms, weights))
    bases = [(f, v) for f, v in constraints if f.args[0] == X]
    if len(bases) != 1:
        raise UnsupportedCondition(
            "one unit-angle extremal series is required for the intersection certificate"
        )
    base, value = bases[0]
    variable = S if base.func == sp.sin else C
    for q in table(variable, value):
        if any(sp.simplify(f.subs(X, q * sp.pi) - v) != 0 for f, v in constraints):
            raise UnsupportedCondition(
                "the complete base family must satisfy every other extremal condition"
            )
    return Equation(
        variable - value, (), sp.S.One, extremum=(raw, reduced, constraints)
    )


def proof(a):
    from .exam_trigonometric_proof import families, pi

    _raw, reduced, constraints = a.extremum
    html = line(a.original) + line(sp.latex(reduced) + "=0")
    html += "<p>Модуль каждой тригонометрической функции не превосходит 1. Сумма достигает суммы верхних границ только тогда, когда каждый член достигает своей границы:</p>"
    for f, v in constraints:
        html += line(r"\left|" + sp.latex(f) + r"\right|\le1")
        html += line(sp.latex(f) + "=" + sp.latex(v))
    html += "<p>Решения должны удовлетворять обоим уравнениям одновременно. Проверим всю серию уравнения с единичным углом:</p>"
    for text in families(a):
        html += line(text + r",\quad k\in\mathbb Z")
    q, p = a.series[0]
    k = sp.Symbol("k", integer=True)
    for f, v in constraints:
        if f.args[0] == X:
            continue
        variable = S if f.func == sp.sin else C
        target = table(variable, v)[0]
        multiple = sp.cancel(f.args[0] / X)
        index = sp.expand((multiple * (q + p * k) - target) / 2)
        if index.is_integer is not True:
            raise UnsupportedCondition(
                "the second extremal family must have an integer index for every base index"
            )
        html += line(
            sp.latex(f)
            + "="
            + sp.latex(v)
            + r"\quad\Longleftrightarrow\quad "
            + sp.latex(multiple * X)
            + "="
            + pi(target)
            + r"+2\pi n"
        )
        n = sp.Symbol("n", integer=True)
        html += line(
            sp.latex((q + p * k) * sp.pi)
            + "="
            + sp.latex((target + 2 * n) * sp.pi / multiple)
        )
        html += line("n=" + sp.latex(index) + r"\in\mathbb Z")
    html += "<p>Поэтому все члены первой серии удовлетворяют всей системе:</p>"
    return (
        "<p>Используем формулу произведения в сумму и оценим каждое слагаемое:</p>",
        html,
    )
