"""Keep y, reciprocal t, rational inverse signs and quadratic exponent branches."""

import sympy as sp

from ..probability.common import line
from .exponential_inequality_preimage_proof import alternatives, return_branch
from .exponential_inequality_proof import power
from .exponential_nested_reciprocal import positive_case, y_cases
from .rational_inequality_proof import RELATION


def cases(name, values):
    rows = [alternatives(name, value) for value in values]
    if not rows:
        return alternatives(name, sp.EmptySet)
    if len(rows) == 1:
        return rows[0]
    return r"\left[\begin{aligned}" + r"\\".join(rows) + r"\end{aligned}\right."


def render(a):
    actual = power(a.base, a.exponent)
    A, B, C = a.coefficients
    y = sp.Symbol("y")
    y_value = sp.Add(A / y**2, B / y, C, evaluate=False)
    html = "<p>Пусть новая переменная равна выражению в знаменателе. Исходный знаменатель не должен обращаться в ноль:</p>"
    html += line("y=" + actual + r"-1,\qquad y\ne0")
    html += line(sp.latex(y_value, order="none") + RELATION[a.operator] + "0")
    html += "<p>Введём вторую замену и решим квадратное неравенство:</p>"
    html += line(r"t=\frac{1}{y}")
    html += line(
        sp.latex(a.stage.original).replace("x", "t") + RELATION[a.operator] + "0"
    )
    html += line(alternatives("t", a.stage.solution))
    html += "<p>Вернёмся к переменной y. Она может быть как положительной, так и отрицательной, поэтому решаем рациональные неравенства, сохраняя исключение нуля:</p>"
    html += line(alternatives(r"\frac{1}{y}", a.stage.solution))
    rows = [
        r",\quad ".join(
            sp.latex(sp.together(c.stage.original)).replace("x", "y")
            + ("=" if c.operator == "=" else RELATION[c.operator])
            + "0"
            for c in b.conditions
        )
        for b in a.inverse_branches
    ]
    if rows:
        html += line(
            r"\left[\begin{aligned}" + r"\\".join(rows) + r"\end{aligned}\right."
        )
    ys = y_cases(a.inverse_branches)
    html += line(cases("y", ys))
    html += "<p>Возвращаемся к исходной показательной функции:</p>"
    html += line(cases(actual + "-1", ys))
    html += line(cases(actual, [positive_case(v) for v in ys]))
    html += "<p>Учитываем область значений положительной степени; граничное значение также может давать отдельное решение:</p>"
    html += line(alternatives(actual, a.power_range))
    html += line(cases(actual, [b.values for b in a.branches]))
    html += "<p>Основание больше единицы, поэтому сравниваем показатели и объединяем полученные ветви:</p>"
    for branch in a.branches:
        html += return_branch(a, branch, variable=actual)
    if not a.branches:
        html += line(alternatives("x", sp.EmptySet))
    return html
