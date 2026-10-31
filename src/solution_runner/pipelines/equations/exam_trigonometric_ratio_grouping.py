"""Group a cosine and a tangent factor on the original nonzero cosine domain."""

from dataclasses import replace

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S, T


def proof(a):
    from functools import partial

    from .exam_trigonometric_proof import formula as format_formula
    from .exam_trigonometric_proof import polynomial
    from .exam_trigonometric_variants import argument

    theta = argument(a.scale)
    formula = partial(format_formula, angle=theta)

    if a.cleared_denominator != C or a.preferred != T or a.poles != (C,):
        return None
    expression = sp.cancel(a.factored_source.subs(S, C * T) / C)
    if not expression.is_polynomial(T, C):
        return None
    _, factors = sp.factor_list(expression, T, C, extension=True)
    if len(factors) != 2 or any(
        power != 1
        or f.free_symbols not in ({T}, {C})
        or sp.degree(f, next(iter(f.free_symbols))) != 1
        for f, power in factors
    ):
        return None
    html = "<p>Запишем область определения тангенса:</p>" + line(
        r"\cos " + theta + r"\ne0"
    )
    html += line(a.original)
    html += "<p>В этой области выразим синус через тангенс и сгруппируем слагаемые:</p>"
    html += line(r"\sin " + theta + r"=\cos " + theta + r"\cdot\tg " + theta)
    html += line(formula(expression) + "=0")
    html += line(formula(sp.factor(expression, extension=True)) + "=0")
    html += "<p>Решим каждое уравнение отдельно, сохраняя обе ветви:</p>"
    for branch in a.branches:
        html += polynomial(
            replace(branch, original=None), angle=theta, root_scale=a.scale
        )
    return (
        "<p>Разложим на множители без деления на потенциально нулевой множитель:</p>",
        html,
    )
