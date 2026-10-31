"""Choose a reviewed equation compiler while preserving the parent method."""

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import compile_equation


def method_equation(
    formula,
    preferred,
    scale,
    translation,
    *,
    grouping=False,
    difference=False,
    product=False,
):
    from .exam_trigonometric_absolute import compile_absolute
    from .exam_trigonometric_domain import radical_product
    from .exam_trigonometric_methods import Equation, compile_reviewed
    from .exam_trigonometric_radical_quotient import compile_quotient

    if product:
        from .exam_trigonometric_angle_product import compile_product

        if translation:
            raise UnsupportedCondition(
                "separate angle products require the original variable"
            )
        return compile_product(formula), None
    absolute = compile_absolute(formula)
    if absolute is not None:
        return absolute, None

    quotient = compile_quotient(formula)
    if quotient is not None:
        return quotient, quotient.domain

    product = radical_product(formula)
    if product is not None:
        if translation:
            raise UnsupportedCondition(
                "translated radical products need a reviewed domain"
            )
        raw, identities, domain = product
        return Equation(raw, identities, sp.S.One), domain
    if scale != 1 or translation or difference:
        return compile_reviewed(
            formula, preferred, scale, translation, difference=difference
        ), None
    try:
        raw, identities = compile_equation(formula, allow_cubic=grouping)
    except UnsupportedCondition:
        return compile_reviewed(
            formula, preferred, scale, translation, difference=difference
        ), None
    return Equation(raw, identities, sp.S.One), None
