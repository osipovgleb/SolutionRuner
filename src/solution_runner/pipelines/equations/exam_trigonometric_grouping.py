"""Keep homogeneous linear factors separate, with grouping and original poles."""

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_variants import argument


def proof(a):
    from .exam_trigonometric_proof import formula, polynomial

    factors = [b.original for b in a.branches]
    if len(factors) != 2 or any(sp.Poly(f, S, C).total_degree() != 1 for f in factors):
        raise UnsupportedCondition(
            "two homogeneous linear factors are required for grouping"
        )
    coefficient = sp.cancel(a.raw / sp.prod(factors), extension=True)
    if coefficient.free_symbols or coefficient == 0:
        raise UnsupportedCondition(
            "the factor product must equal the source polynomial"
        )
    if (
        not a.poles
        and factors[0].coeff(C).is_Rational
        and not factors[1].coeff(C).is_Rational
    ):
        factors.reverse()
    first, second = factors[0], sp.expand(coefficient * factors[1])
    grouped = sp.Add(
        *(
            sp.Mul(coef * S ** powers[0] * C ** powers[1], first, evaluate=False)
            for powers, coef in sp.Poly(second, S, C).terms()
        ),
        evaluate=False,
    )
    angle = argument(a.scale)
    html = ""
    if a.poles:
        html += "<p>До сокращения запишем область определения исходного уравнения:</p>"
        for pole in a.poles:
            html += line(formula(pole, angle) + r"\ne0")
    for text, value in a.identities:
        html += line(text + "=" + formula(value, angle))
    if a.poles:
        html += "<p>Сокращаем только множители, ненулевые в исходной области определения:</p>"
    html += line(formula(a.raw, angle) + "=0")
    if not a.poles:
        html += "<p>Сгруппируем слагаемые и вынесем общий множитель:</p>"
        html += line(formula(grouped, angle) + "=0")
    html += line(formula(first * second, angle) + "=0")
    html += "<p>Произведение равно нулю, когда хотя бы один множитель равен нулю:</p>"
    for factor in factors:
        branch = next(b for b in a.branches if b.original == factor)
        html += polynomial(branch, angle=angle, root_scale=a.scale)
    return (
        "<p>Применим формулы приведения и двойного угла, затем разложим на множители:</p>",
        html,
    )


def branches(raw):
    from .exam_trigonometric_ratios import linear_branch

    if raw.free_symbols != {S, C} or not raw.is_polynomial(S, C):
        return None
    factors = sp.factor_list(raw, S, C, extension=True)[1]
    if len(factors) != 2 or any(power != 1 for _, power in factors):
        return None
    result = tuple(linear_branch(f) for f, _ in factors)
    if any(b is None for b in result):
        return None
    return raw, result


def mixed_branches(raw):
    grouped = branches(raw)
    if grouped is not None:
        return grouped
    from .exam_trigonometric_factors import separated

    separate = separated(raw, S, False)
    if separate is not None:
        return separate
    from .exam_trigonometric_combination import branches as combination_branches

    return combination_branches(raw)


def pure_proof(a):
    from .exam_trigonometric_proof import formula, polynomial

    common = next(b.polynomial for b in a.branches if b.grouping)
    quotient = sp.cancel(a.raw / common, extension=True)
    if not quotient.is_polynomial(S, C) or sp.Poly(quotient, S, C).total_degree() != 1:
        raise UnsupportedCondition(
            "the common affine factor must divide the source polynomial"
        )
    expression = sp.Add(
        *(
            sp.Mul(coef * S ** powers[0] * C ** powers[1], common, evaluate=False)
            for powers, coef in sp.Poly(quotient, S, C).terms()
        ),
        evaluate=False,
    )
    html = "".join(line(text + "=" + formula(value)) for text, value in a.identities)
    html += line(formula(a.raw) + "=0")
    html += "<p>Сгруппируем слагаемые и вынесем общий множитель:</p>"
    html += line(formula(expression) + "=0") + line(formula(common * quotient) + "=0")
    html += "<p>Произведение равно нулю, когда хотя бы один множитель равен нулю:</p>"
    for branch in a.branches:
        html += polynomial(branch)
    return "<p>Применим формулу двойного угла и сгруппируем слагаемые:</p>", html
