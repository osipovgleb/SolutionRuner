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
    preserve_products=False,
    square_sum=False,
):
    from .exam_trigonometric_absolute import compile_absolute
    from .exam_trigonometric_domain import radical_product
    from .exam_trigonometric_methods import Equation, compile_reviewed
    from .exam_trigonometric_radical_quotient import compile_quotient
    from .exam_trigonometric_sum_product import compile_reciprocal, compile_square

    if square_sum:
        if translation:
            raise UnsupportedCondition(
                "sum-to-product methods require the original variable"
            )
        return compile_square(formula), None
    reciprocal = compile_reciprocal(formula)
    if reciprocal is not None:
        return reciprocal, None
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
            formula,
            preferred,
            scale,
            translation,
            difference=difference,
            preserve_products=preserve_products,
        ), None
    try:
        raw, identities = compile_equation(formula, allow_cubic=grouping)
    except UnsupportedCondition:
        return compile_reviewed(
            formula,
            preferred,
            scale,
            translation,
            difference=difference,
            preserve_products=preserve_products,
        ), None
    return Equation(raw, identities, sp.S.One), None


def analysis_fields(equation):
    return {
        "scale": equation.scale,
        "poles": equation.poles,
        "reciprocal": equation.reciprocal,
        "doubled": equation.doubled,
        "rewritten": equation.rewritten,
        "strict_domain": equation.strict_domain,
        "fraction": equation.fraction,
        "absolute": equation.absolute,
        "homogeneous": equation.homogeneous,
        "power_angle": equation.power_angle,
        "factored_source": equation.factored_source,
        "affine": equation.affine,
        "angle_product": equation.angle_product,
        "cleared_denominator": equation.cleared_denominator,
        "square_difference": equation.square_difference,
        "symmetric": equation.symmetric,
        "square_product": equation.square_product,
        "unit_factors": equation.unit_factors,
        "sum_product": equation.sum_product,
    }
