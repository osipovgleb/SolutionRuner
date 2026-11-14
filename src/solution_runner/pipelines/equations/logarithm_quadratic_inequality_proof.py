"""Keep the parent's direct quadratic treatment and separate logarithmic alternatives."""

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_quadratic_proof import expression
from .rational_inequality import FLIPPED
from .rational_inequality_parser import X, polynomial
from .rational_inequality_proof import RELATION


def empty_branch(condition):
    p = polynomial(condition.stage.original)
    if p.degree() != 2 or condition.stage.solution != sp.EmptySet:
        return ""
    vertex = -p.nth(1) / (2 * p.nth(2))
    extreme = p.eval(vertex)
    if p.nth(2) < 0 and extreme < 0 and condition.stage.operator in (">", ">="):
        completed = p.nth(2) * (X - vertex) ** 2 + extreme
        return (
            line(sp.latex(p.as_expr()) + "=" + sp.latex(completed) + "<0")
            + "<p>Левая часть всегда отрицательна, поэтому эта ветвь решений не имеет.</p>"
        )
    return ""


def argument_conditions(a, *, expanded):
    if not a.branches:
        raise UnsupportedCondition(
            "this parent presentation requires a nonempty logarithm domain"
        )
    rows = []
    for branch in a.branches:
        conditions = []
        for c in branch.conditions:
            if expanded:
                text = sp.latex(c.stage.original) + RELATION[c.stage.operator] + "0"
            else:
                op = (
                    c.operator
                    if a.base > 1 or c.operator == "="
                    else FLIPPED[c.operator]
                )
                text = (
                    sp.latex(a.argument)
                    + ("=" if op == "=" else RELATION[op])
                    + sp.latex(a.base**c.bound)
                )
            conditions.append(text)
        rows.append(
            conditions[0]
            if len(conditions) == 1
            else r"\begin{cases}" + r"\\".join(conditions) + r"\end{cases}"
        )
    alternatives = r"\left[\begin{aligned}" + r"\\".join(rows) + r"\end{aligned}\right."
    return line(
        r"\begin{cases}"
        + sp.latex(a.argument)
        + ">0"
        + r"\\"
        + alternatives
        + r"\end{cases}"
    )


def render(a, *, method="quadratic"):
    if method not in ("quadratic", "quadratic_substitution"):
        raise UnsupportedCondition(
            "one reviewed quadratic logarithm presentation is required"
        )
    substitution = method == "quadratic_substitution"
    actual = (
        r"\log_{" + sp.latex(a.base) + r"}\left(" + sp.latex(a.argument) + r"\right)"
    )
    relation = RELATION[a.operator] + "0"
    if substitution:
        html = "<p>Обозначим логарифм через t на исходной области определения:</p>"
        html += line("t=" + actual + r",\quad " + sp.latex(a.argument) + ">0")
    else:
        html = "<p>Решение неравенства ищем при условии положительности аргумента:</p>"
        html += line(sp.latex(a.argument) + ">0")
        if a.argument != X:
            html += line(alternatives("x", a.domain))
    if a.reciprocal_base:
        html += "<p>Логарифм с обратным основанием заменим противоположным логарифмом с выбранным основанием:</p>"
        html += line(
            r"\log_{"
            + sp.latex(1 / a.base)
            + r"}\left("
            + sp.latex(a.argument)
            + r"\right)=-"
            + actual
        )
    html += (
        "<p>Получаем квадратное неравенство относительно t. Разложим трёхчлен на множители:</p>"
        if substitution
        else "<p>Решим неравенство как квадратное относительно логарифма. Перенесём все слагаемые влево и разложим квадратный трёхчлен на множители:</p>"
    )
    variable = "t" if substitution else actual
    html += line(expression(a.stage.original, variable) + relation)
    html += line(expression(sp.factor(a.stage.original), variable) + relation)
    html += line(alternatives(variable, a.stage.solution))
    if substitution:
        html += line(alternatives(actual, a.stage.solution))
    html += (
        (
            "<p>Вернёмся к исходной переменной. Основание "
            if substitution
            else "<p>Основание "
        )
        + ("больше" if a.base > 1 else "меньше")
        + " единицы, поэтому при переходе к аргументу знак "
        + ("сохраняется" if a.base > 1 else "меняется")
        + ". Каждую ветвь решаем отдельно с учётом области определения:</p>"
    )
    if substitution:
        html += argument_conditions(a, expanded=False)
        html += argument_conditions(a, expanded=True)
        for branch in a.branches:
            for condition in branch.conditions:
                html += empty_branch(condition)
        return (
            html
            + "<p>Объединим решения полученных ветвей с учётом области определения:</p>"
            + line(alternatives("x", a.solution))
        )
    for branch in a.branches:
        rows = [sp.latex(a.argument) + ">0"]
        for condition in branch.conditions:
            op = (
                condition.operator
                if a.base > 1 or condition.operator == "="
                else FLIPPED[condition.operator]
            )
            rows.append(
                sp.latex(a.argument)
                + ("=" if op == "=" else RELATION[op])
                + sp.latex(a.base**condition.bound)
            )
        html += line(r"\begin{cases}" + r"\\".join(rows) + r"\end{cases}")
        html += line(alternatives("x", branch.solution))
    html += "<p>Объединим решения полученных ветвей:</p>"
    return html + line(alternatives("x", a.solution))
