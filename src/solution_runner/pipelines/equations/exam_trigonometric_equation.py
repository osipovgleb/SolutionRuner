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
        return product, product.domain
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
        "absolute_square": equation.absolute_square,
        "absolute_fraction": equation.absolute_fraction,
        "radical_ratio": equation.radical_ratio,
        "radical_product": equation.radical_product,
        "radical_equation": equation.radical_equation,
        "bounded_log": equation.bounded_log,
        "log_product": equation.log_product,
        "log_polynomial": equation.log_polynomial,
        "global_radical": equation.global_radical,
        "square_radicals": equation.square_radicals,
        "sum_squares": equation.sum_squares,
        "argument_pair": equation.argument_pair,
        "extremum": equation.extremum,
        "sine_pair": equation.sine_pair,
        "cosine_equality": equation.cosine_equality,
        "sine_double": equation.sine_double,
        "positive_factorization": equation.positive_factorization,
        "homogeneous": equation.homogeneous,
        "power_angle": equation.power_angle,
        "factored_source": equation.factored_source,
        "affine": equation.affine,
        "angle_product": equation.angle_product,
        "cleared_denominator": equation.cleared_denominator,
        "ratio_division": equation.ratio_division,
        "square_difference": equation.square_difference,
        "symmetric": equation.symmetric,
        "square_product": equation.square_product,
        "unit_factors": equation.unit_factors,
        "sum_product": equation.sum_product,
        "triple_angle": equation.triple_angle,
        "ratio_product": equation.ratio_product,
    }


def compile_parent(formula, preferred, preferred_scale, translation, parent_html):
    from .exam_trigonometric_absolute_square import reviewed as square_absolute
    from .exam_trigonometric_angle_product import reviewed as angle_product_method
    from .exam_trigonometric_extremum import reviewed as extremum_method
    from .exam_trigonometric_factor_style import base_angle_product
    from .exam_trigonometric_ratio_product import style as ratio_product_style
    from .exam_trigonometric_sine_pair import reviewed as sine_pair_method
    from .exam_trigonometric_square_difference import reviewed as difference_method
    from .exam_trigonometric_square_factor import reviewed as square_method
    from .exam_trigonometric_style import grouping_method
    from .exam_trigonometric_sum_identities import style as sum_identity_style
    from .exam_trigonometric_sum_product import square_style
    from .exam_trigonometric_triple_angle import style as triple_angle_style

    if translation and (
        square_absolute(parent_html)
        or extremum_method(parent_html)
        or sine_pair_method(parent_html)
    ):
        raise UnsupportedCondition(
            "these reviewed methods require the original angle variable"
        )
    from .exam_trigonometric_absolute_fraction import reviewed as absolute_fraction
    from .exam_trigonometric_cosine_equality import reviewed as cosine_equality
    from .exam_trigonometric_positive_factors import reviewed as positive_factors

    compiled = compile_constrained(formula, parent_html, translation)
    if compiled is not None:
        domain = compiled.domain
    elif cosine_equality(parent_html):
        from .exam_trigonometric_cosine_equality import compile_equality

        if translation:
            raise UnsupportedCondition(
                "cosine argument equality requires the original variable"
            )
        compiled, domain = compile_equality(formula), None
    elif absolute_fraction(parent_html):
        from .exam_trigonometric_absolute_fraction import compile_fraction

        if translation:
            raise UnsupportedCondition(
                "absolute-denominator cases require the original angle"
            )
        compiled = compile_fraction(formula)
        domain = compiled.domain
    elif positive_factors(parent_html):
        from .exam_trigonometric_positive_factors import compile_factor

        if translation:
            raise UnsupportedCondition(
                "positive-factor identities require the original angle"
            )
        compiled, domain = compile_factor(formula), None
    elif square_absolute(parent_html):
        from .exam_trigonometric_absolute_square import compile_square

        compiled = compile_square(formula, preferred, preferred_scale)
        domain = compiled.domain
    elif extremum_method(parent_html):
        from .exam_trigonometric_extremum import compile_extremum

        compiled, domain = compile_extremum(formula), None
    elif sine_pair_method(parent_html):
        from .exam_trigonometric_sine_pair import compile_pair

        compiled, domain = compile_pair(formula), None
    else:
        compiled, domain = method_equation(
            formula,
            preferred,
            preferred_scale,
            translation,
            grouping=grouping_method(parent_html),
            difference=difference_method(parent_html),
            product=angle_product_method(parent_html),
            preserve_products=square_method(parent_html)
            or base_angle_product(parent_html),
            square_sum=square_style(parent_html),
            sum_identity=sum_identity_style(parent_html),
            triple_angle=triple_angle_style(parent_html),
            ratio_product=ratio_product_style(parent_html),
        )
    from .exam_trigonometric_pole_proof import prepare_division
    from .exam_trigonometric_sine_double import prepare as sine_double

    compiled = prepare_division(compiled, formula, parent_html)
    compiled = sine_double(compiled, preferred, preferred_scale)
    return compiled, domain


def compile_constrained(formula, parent_html, translation):
    from .exam_trigonometric_bounded_log import reviewed as bounded_log
    from .exam_trigonometric_global_radical import reviewed as global_radical
    from .exam_trigonometric_radical_equation import variable_radicals
    from .exam_trigonometric_radical_style import kind as radical_kind
    from .exam_trigonometric_sum_squares import reviewed as sum_squares

    if bounded_log(parent_html):
        from .exam_trigonometric_bounded_log import compile_log

        if translation:
            raise UnsupportedCondition(
                "bounded logarithms require their original x domain"
            )
        compiled = compile_log(formula)
    elif r"\log_" in formula and not variable_radicals(formula):
        from .exam_trigonometric_log_product import compile_product, prepare

        if translation:
            raise UnsupportedCondition("log products require the original variable")
        from .exam_trigonometric_log_polynomial import compile_polynomial

        compiled = compile_polynomial(formula, parent_html)
        if compiled is None:
            compiled = prepare(compile_product(formula), parent_html)
    elif global_radical(parent_html):
        from .exam_trigonometric_global_radical import compile_global

        if translation:
            raise UnsupportedCondition("global radical domains require physical x")
        compiled = compile_global(formula, global_radical(parent_html))
    elif radical_kind(parent_html) and variable_radicals(formula):
        from .exam_trigonometric_radical_product import operands

        if operands(formula) is not None:
            return None
        from .exam_trigonometric_radical_equation import compile_radical

        if translation:
            raise UnsupportedCondition(
                "the reviewed radical equation requires its original variable"
            )
        if radical_kind(parent_html) == "perfect_squares":
            from .exam_trigonometric_radical_style import square_method
            from .exam_trigonometric_square_radicals import compile_squares

            compiled = compile_squares(formula, square_method(parent_html))
        else:
            compiled = compile_radical(formula, radical_kind(parent_html))
    elif sum_squares(parent_html):
        from .exam_trigonometric_sum_squares import compile_squares

        if translation:
            raise UnsupportedCondition(
                "the two-square system requires the original angle"
            )
        compiled = compile_squares(formula)
    else:
        return None
    return compiled
