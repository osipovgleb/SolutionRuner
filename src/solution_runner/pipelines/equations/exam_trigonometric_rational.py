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
    if not variables or not variables <= {S, C}:
        raise UnsupportedCondition("the original poles must use sine and cosine")
    if any(
        not p.is_polynomial(S, C) or sp.Poly(p, S, C).total_degree() > 2 for p in poles
    ):
        raise UnsupportedCondition(
            "the original poles must be bounded function polynomials"
        )
    expression = (
        (values[0] - values[1])
        .xreplace(compiled)
        .xreplace({NUMERIC_S: S, NUMERIC_C: C})
    )
    expression, complements = complement_denominators(expression, scale)
    identities += complements
    expression = sp.together(expression)
    numerator, denominator = sp.fraction(expression)
    functions = numerator.free_symbols
    if (
        numerator == 0
        or len(functions) != 1
        or not functions <= {S, C}
        or not numerator.is_polynomial(*functions)
        or sp.degree(numerator, next(iter(functions))) not in (1, 2)
        or denominator.free_symbols - {S, C}
    ):
        raise UnsupportedCondition(
            "the uncancelled numerator must be linear or quadratic in one function"
        )
    return Equation(sp.expand(numerator), identities, scale, poles, fraction=expression)


def complement_denominators(expression, scale):
    replacements = {}
    identities = []
    angle = sp.latex(scale * sp.Symbol("x", real=True))
    for power in expression.atoms(sp.Pow):
        if not power.exp.is_Integer or power.exp >= 0:
            continue
        for variable, other in ((C, S), (S, C)):
            coefficient = sp.cancel(power.base / (1 - variable**2))
            if coefficient and not coefficient.free_symbols:
                replacement = coefficient * other**2
                replacements[power.base] = replacement
                text = sp.latex(
                    power.base,
                    symbol_names={S: r"\sin(" + angle + ")", C: r"\cos(" + angle + ")"},
                )
                identities.append((text, replacement))
                break
    return expression.xreplace(replacements), tuple(identities)


def proof(a):
    from .exam_trigonometric_proof import formula, polynomial

    if len(a.branches) != 1:
        raise UnsupportedCondition("one rational function substitution is required")
    branch = a.branches[0]
    if (
        len(a.fraction.free_symbols) > 1
        or sp.degree(branch.polynomial, branch.variable) == 1
        or (
            not a.substitution
            and len(set().union(*(p.free_symbols for p in a.poles))) > 1
        )
    ):
        return direct_proof(a, branch)
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
        sine_inverse=a.sine_inverse,
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


def direct_proof(a, branch):
    from .exam_trigonometric_proof import formula, polynomial
    from .exam_trigonometric_variants import argument

    angle = argument(a.scale)
    html = "<p>Запишем ограничения исходной дроби до сокращения:</p>"
    for pole in a.poles:
        html += line(formula(pole, angle) + r"\ne0")
    html += line(a.original)
    for text, value in a.identities:
        if value not in (S, C):
            html += line(text + "=" + formula(value, angle))
    html += "<p>На этой области определения используем формулы приведения и сокращаем только ненулевые множители:</p>"
    html += line(formula(a.fraction, angle) + "=0")
    html += "<p>Числитель должен равняться нулю, а исходный знаменатель — оставаться ненулевым:</p>"
    html += line(formula(sp.factor(a.raw, extension=True), angle) + "=0")
    html += polynomial(
        branch,
        angle=angle,
        root_scale=a.scale,
        allowed_residues=branch.residues,
        allow_inverse=a.allow_inverse,
        factorization=a.factorization,
        sine_inverse=a.sine_inverse,
    )
    html += "<p>В каждой серии оставлены только корни, не обращающие исходный знаменатель в нуль.</p>"
    return "<p>Решим уравнение с сохранением области определения дроби:</p>", html
