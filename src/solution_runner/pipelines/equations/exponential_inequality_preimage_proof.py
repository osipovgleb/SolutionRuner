"""Keep the parent's range system or separate quadratic back-substitution branches."""

from functools import partial

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from ..word_problems.water_season_proof import inline
from .exponential_inequality_proof import power
from .exponential_inequality_quadratic_labels import level_text
from .exponential_inequality_quadratic_proof import (
    expanded,
    expression,
    factor_step,
    membership,
)
from .rational_inequality import FLIPPED
from .rational_inequality_parser import X, polynomial
from .rational_inequality_proof import RELATION

METHODS = ("quadratic_range", "quadratic_branches")


def alternatives(name, solution, endpoint=sp.latex):
    if isinstance(solution, sp.Union):
        rows = [alternatives(name, part, endpoint) for part in solution.args]
        return r"\left[\begin{aligned}" + r"\\".join(rows) + r"\end{aligned}\right."
    if isinstance(solution, sp.FiniteSet) and len(solution) == 1:
        return name + "=" + endpoint(next(iter(solution)))
    if isinstance(solution, sp.Interval) and solution.end == sp.oo:
        return (
            name
            + (r"\gt " if solution.left_open else r"\ge ")
            + endpoint(solution.start)
        )
    return membership(name, solution, endpoint=endpoint)


def validation(a, method):
    if (
        method not in METHODS
        or len(a.stage.zeros) != 2
        or any(t.is_positive is not True for t in a.stage.zeros)
    ):
        raise UnsupportedCondition(
            "these quadratic-exponent parents need two positive polynomial roots"
        )
    reciprocal = method == "quadratic_range"
    if a.multiply_degree != int(reciprocal) or any(
        k not in ((-1, 0, 1) if reciprocal else (0, 1, 2)) for k, _ in a.coefficients
    ):
        raise UnsupportedCondition(
            "the positive-power degrees must match the reviewed parent method"
        )
    if reciprocal and polynomial(a.exponent).LC() <= 0:
        raise UnsupportedCondition(
            "this range parent requires an upward quadratic exponent"
        )


def range_preparation(a):
    actual = power(a.base, a.exponent)
    p = polynomial(a.exponent)
    vertex = -p.nth(1) / (2 * p.nth(2))
    extreme = p.eval(vertex)
    html = (
        "<p>Сделаем замену. Квадратичный показатель имеет наименьшее значение "
        + inline(sp.latex(extreme))
        + ":</p>"
    )
    completed = p.nth(2) * (X - vertex) ** 2 + extreme
    html += line(
        (sp.latex(a.exponent) + "=" if completed != a.exponent else "")
        + sp.latex(completed)
        + r"\ge "
        + sp.latex(extreme)
    )
    html += line("t=" + actual + r"\ge " + sp.latex(a.power_range.start))
    html += "<p>Тогда исходное неравенство принимает вид:</p>"
    html += line(expanded(a, "t", reciprocal=True) + RELATION[a.operator] + "0")
    html += "<p>Умножим обе части на положительное t, не меняя знака неравенства, и сохраним условие на замену:</p>"
    html += line(
        r"\begin{cases}"
        + expression(a.stage.original, "t")
        + RELATION[a.operator]
        + "0"
        + r"\\t\ge "
        + sp.latex(a.power_range.start)
        + r"\end{cases}"
    )
    html += factor_step(a, a.stage.original, "t")
    return html + line(alternatives("t", a.reachable_solution))


def branch_preparation(a):
    html = (
        "<p>Пусть "
        + inline("t=" + power(a.base, a.exponent) + ">0")
        + ". Тогда неравенство примет вид:</p>"
    )
    html += line(expression(a.stage.original, "t") + RELATION[a.operator] + "0")
    html += factor_step(a, a.stage.original, "t")
    # Positivity is already stated; zero is only a limit of the substitution.
    rows = []
    for b in a.branches:
        rows.append(
            r",\quad ".join(
                "t" + RELATION[c.operator] + sp.latex(c.bound) for c in b.conditions
            )
        )
    return html + line(
        r"\left[\begin{aligned}" + r"\\".join(rows) + r"\end{aligned}\right."
    )


def return_branch(a, b):
    actual = power(a.base, a.exponent)
    text = r",\quad ".join(
        "t" + ("=" if c.operator == "=" else RELATION[c.operator]) + sp.latex(c.bound)
        for c in b.conditions
    )
    html = "<p>При " + inline(text) + " получим:</p>"
    for c in b.conditions:
        relation = "=" if c.operator == "=" else RELATION[c.operator]
        html += line(actual + relation + sp.latex(c.bound))
        html += line(
            sp.latex(a.exponent) + relation + level_text(a.base, c.bound, c.value)
        )
        if c.value.is_Rational and (c.value != 0 or polynomial(a.exponent).LC() < 0):
            value = sp.expand(a.exponent - c.value)
            if polynomial(a.exponent).LC() < 0:
                html += (
                    "<p>Умножим на -1, меняя знак неравенства.</p>"
                    if c.operator != "="
                    else "<p>Умножим равенство на -1.</p>"
                )
                value = -value
                relation = "=" if c.operator == "=" else RELATION[FLIPPED[c.operator]]
            html += line(sp.latex(sp.expand(value)) + relation + "0")
    return html + line(alternatives("x", b.solution, a.endpoint))


def render(a, *, method):
    validation(a, method)
    ranged = method == "quadratic_range"
    html = line(a.formula) + (range_preparation(a) if ranged else branch_preparation(a))
    html += (
        "<p>Возвращаемся к исходной переменной. Основание "
        + inline(sp.latex(a.base) + ">1")
        + ", поэтому сравнение степеней равносильно сравнению показателей. Ветви объединяем:</p>"
    )
    for b in a.reachable_branches if ranged else a.branches:
        html += return_branch(a, b)
    return html + line(r"x\in " + a.answer)


RENDERS = {method: partial(render, method=method) for method in METHODS}
