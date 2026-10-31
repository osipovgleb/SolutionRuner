"""Keep uncancelled numerators and every original pole of a function fraction."""

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .trig_angles import C as NUMERIC_C
from .trig_angles import S as NUMERIC_S


def compile_fraction(values, compiled, poles, scale, identities):
    from .exam_trigonometric_methods import Equation

    variables = set().union(*(p.free_symbols for p in poles))
    if scale != 1 or len(variables) != 1 or not variables <= {S, C}:
        raise UnsupportedCondition(
            "one unscaled sine or cosine is required for a rational substitution"
        )
    variable = next(iter(variables))
    if any(not p.is_polynomial(variable) or sp.degree(p, variable) > 2 for p in poles):
        raise UnsupportedCondition(
            "the original poles must be bounded function polynomials"
        )
    expression = sp.together(
        (values[0] - values[1])
        .xreplace(compiled)
        .xreplace({NUMERIC_S: S, NUMERIC_C: C})
    )
    numerator, denominator = sp.fraction(expression)
    if (
        numerator == 0
        or not numerator.is_polynomial(variable)
        or sp.degree(numerator, variable) != 2
        or denominator.free_symbols - {variable}
    ):
        raise UnsupportedCondition(
            "the uncancelled numerator must be a quadratic in one function"
        )
    return Equation(
        sp.expand(numerator), identities, sp.S.One, poles, fraction=expression
    )


def proof(a):
    from .exam_trigonometric_proof import formula, polynomial

    if len(a.branches) != 1:
        raise UnsupportedCondition("one rational function substitution is required")
    branch = a.branches[0]
    name = a.substitution or "t"
    parameter = sp.Symbol(name, real=True)
    html = (
        "<p>До приведения к общему знаменателю запишем ограничения исходных дробей:</p>"
    )
    for pole in a.poles:
        html += line(formula(pole) + r"\ne0")
    html += "<p>Сделаем замену:</p>" + line(name + "=" + formula(branch.variable))
    html += "<p>Приведём к общему знаменателю без потери исходных ограничений:</p>"
    html += line(sp.latex(a.fraction.subs(branch.variable, parameter)) + "=0")
    html += polynomial(
        branch,
        substitution=name,
        allowed_residues=branch.residues,
        factorization=a.factorization,
    )
    for value in branch.excluded:
        html += (
            "<p>При "
            + name
            + " = "
            + str(value)
            + " один из исходных знаменателей равен нулю; это значение исключено.</p>"
        )
    return (
        "<p>Решим рациональное уравнение относительно тригонометрической функции:</p>",
        html,
    )
