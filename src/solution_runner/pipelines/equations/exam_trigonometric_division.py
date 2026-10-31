"""Keep the zero branch before dividing a polynomial by its trigonometric factor."""

from dataclasses import replace

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import table


def proof(branch, angle, scale):
    from .exam_trigonometric_proof import (
        candidate_lines,
        formula,
        polynomial,
        series_lines,
    )

    variable = branch.variable
    if branch.polynomial.subs(variable, 0) != 0 or 0 not in branch.values:
        raise UnsupportedCondition("guarded division requires a valid zero branch")
    quotient = sp.cancel(branch.polynomial / variable)
    if not quotient.is_polynomial(variable) or sp.degree(quotient, variable) > 2:
        raise UnsupportedCondition("the remaining factor must be linear or quadratic")
    zero = replace(
        branch,
        polynomial=variable,
        candidates=(sp.S.Zero,),
        values=(sp.S.Zero,),
        residues=table(variable, 0),
    )
    remainder = replace(
        branch,
        polynomial=quotient,
        candidates=tuple(v for v in branch.candidates if v != 0),
        values=tuple(v for v in branch.values if v != 0),
    )
    html = "<p>Сначала сохраним значения, при которых тригонометрический множитель равен нулю:</p>"
    html += candidate_lines(zero, angle=angle, root_scale=scale)
    html += "<p>При прочих значениях переменной множитель отличен от нуля, поэтому только в этой ветви можно разделить обе части уравнения на него:</p>"
    html += line(formula(variable, angle) + r"\ne0")
    if sp.degree(quotient, variable) == 2 and quotient.coeff(variable) == 0:
        value = sp.cancel(-quotient.subs(variable, 0) / quotient.coeff(variable, 2))
        html += line(formula(variable**2, angle) + "=" + sp.latex(value))
        html += candidate_lines(remainder, angle=angle, root_scale=scale)
        html += "<p>Объединим серии для квадрата функции с учётом его периода π по базовому углу:</p>"
        for text in series_lines(
            tuple((q / scale, p / scale) for q, p in series((branch,))[1:])
        ):
            html += line(text + r",\quad k\in\mathbb Z")
    else:
        html += polynomial(remainder, angle=angle, root_scale=scale)
    return html


def series(branches):
    from .exam_trigonometric_inverse import level_series

    if len(branches) != 1 or 0 not in branches[0].values:
        raise UnsupportedCondition(
            "guarded division requires one polynomial with a zero branch"
        )
    branch = branches[0]
    variable = branch.variable
    quotient = sp.cancel(branch.polynomial / variable)
    result = level_series(variable, sp.S.Zero)
    nonzero = tuple(v for v in branch.values if v != 0)
    if sp.degree(quotient, variable) == 2 and quotient.coeff(variable) == 0:
        offsets = sorted({q % 1 for v in nonzero for q in table(variable, v)})
        return result + tuple((q, sp.S.One) for q in offsets)
    return result + tuple(s for v in nonzero for s in level_series(variable, v))
