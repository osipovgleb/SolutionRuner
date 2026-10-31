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
    sum_identity=None,
    triple_angle=None,
    ratio_product=None,
):
    from .exam_trigonometric_absolute import compile_absolute
    from .exam_trigonometric_domain import radical_product
    from .exam_trigonometric_methods import Equation, compile_reviewed
    from .exam_trigonometric_radical_quotient import compile_quotient
    from .exam_trigonometric_sum_product import compile_reciprocal, compile_square

    if ratio_product is not None:
        from .exam_trigonometric_ratio_product import compile_product

        if translation:
            raise UnsupportedCondition(
                "the ratio product requires its original variable"
            )
        return compile_product(formula, ratio_product), None

    if triple_angle and triple_angle[0]:
        from .exam_trigonometric_triple_angle import compile_triple

        if translation:
            raise UnsupportedCondition(
                "the triple-angle identity requires the original variable"
            )
        return compile_triple(formula, triple_angle[1]), None
    if sum_identity:
        from .exam_trigonometric_sum_identities import compile_identity

        if translation:
            raise UnsupportedCondition("sum identities require the original variable")
        return compile_identity(formula, sum_identity), None
    if square_sum:
        if translation:
            raise UnsupportedCondition(
                "sum-to-product methods require the original variable"
            )
        return compile_square(formula), None
    quotient = compile_quotient(formula, product=product)
    if quotient is not None:
        if translation:
            raise UnsupportedCondition(
                "a radical quotient requires its original variable"
            )
        return quotient, quotient.domain
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
        "triple_angle": equation.triple_angle,
        "ratio_product": equation.ratio_product,
    }
