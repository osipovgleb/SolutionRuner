"""Keep the parent's direct quadratic treatment and separate logarithmic alternatives."""

import sympy as sp

from ..probability.common import line
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_quadratic_proof import expression
from .rational_inequality import FLIPPED
from .rational_inequality_parser import X
from .rational_inequality_proof import RELATION


def render(a):
    actual = (
        r"\log_{" + sp.latex(a.base) + r"}\left(" + sp.latex(a.argument) + r"\right)"
    )
    relation = RELATION[a.operator] + "0"
    html = "<p>Решение неравенства ищем при условии положительности аргумента:</p>"
    html += line(sp.latex(a.argument) + ">0")
    if a.argument != X:
        html += line(alternatives("x", a.domain))
    html += "<p>Решим неравенство как квадратное относительно логарифма. Перенесём все слагаемые влево и разложим квадратный трёхчлен на множители:</p>"
    html += line(expression(a.stage.original, actual) + relation)
    html += line(expression(sp.factor(a.stage.original), actual) + relation)
    html += line(alternatives(actual, a.stage.solution))
    html += (
        "<p>Основание "
        + ("больше" if a.base > 1 else "меньше")
        + " единицы, поэтому при переходе к аргументу знак "
        + ("сохраняется" if a.base > 1 else "меняется")
        + ". Каждую ветвь решаем отдельно с учётом области определения:</p>"
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
