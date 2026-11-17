"""Choose a reviewed equation compiler while preserving the parent method."""

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import compile_equation
from .exam_trigonometric_compiler_variants import (
    _compile_log_product,
    _early_power,
    _preferred_method,
    _remaining_constrained,
)
from .exam_trigonometric_models import analysis_fields as _analysis_fields

analysis_fields = _analysis_fields


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
    parent_html="",
):
    from .exam_trigonometric_absolute import compile_absolute
    from .exam_trigonometric_domain import radical_product
    from .exam_trigonometric_methods import Equation, compile_reviewed
    from .exam_trigonometric_radical_quotient import compile_quotient
    from .exam_trigonometric_sum_product import compile_reciprocal

    special = _preferred_method(
        formula,
        parent_html,
        scale,
        translation,
        (ratio_product, triple_angle, sum_identity, square_sum),
    )
    if special is not None:
        return special
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

    compiled = compile_constrained(
        formula, parent_html, translation, preferred=preferred, scale=preferred_scale
    )
    if compiled is not None:
        domain = compiled.domain
    elif cosine_equality(parent_html):
        from .exam_trigonometric_cosine_equality import compile_equality

        if translation:
            raise UnsupportedCondition(
                "cosine argument equality requires the original variable"
            )
        compiled, domain = compile_equality(formula, parent_html=parent_html), None
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
            parent_html=parent_html,
        )
    from .exam_trigonometric_affine import prepare as prepare_affine
    from .exam_trigonometric_pole_proof import prepare_division
    from .exam_trigonometric_sine_double import prepare as sine_double

    compiled = prepare_affine(compiled, parent_html)
    compiled = prepare_division(compiled, formula, parent_html)
    compiled = sine_double(
        compiled, preferred, preferred_scale, formula=formula, parent_html=parent_html
    )
    return compiled, domain


def compile_constrained(
    formula, parent_html, translation, *, preferred=None, scale=sp.S.One
):
    from .exam_trigonometric_bounded_log import reviewed as bounded_log
    from .exam_trigonometric_exponential_absolute import (
        reviewed as exponential_absolute,
    )
    from .exam_trigonometric_radical_equation import variable_radicals

    compiled = _early_power(formula, parent_html, translation, preferred, scale)
    if compiled is not None:
        return compiled
    if exponential_absolute(formula):
        from .exam_trigonometric_exponential_absolute import compile_absolute

        if translation:
            raise UnsupportedCondition(
                "absolute exponents require the original variable"
            )
        compiled = compile_absolute(formula, parent_html)
    elif bounded_log(parent_html):
        from .exam_trigonometric_bounded_log import compile_log

        if translation:
            raise UnsupportedCondition(
                "bounded logarithms require their original x domain"
            )
        compiled = compile_log(formula)
    elif r"\log_" in formula and variable_radicals(formula):
        from .exam_trigonometric_log_radical import (
            compile_inverse,
            compile_product,
            inverse_power,
        )

        if translation:
            raise UnsupportedCondition(
                "radical-log products require their original variable"
            )
        compiled = (
            compile_inverse(formula, parent_html)
            if inverse_power(formula) is not None
            else compile_product(formula, parent_html)
        )
    elif r"\log_" in formula and not variable_radicals(formula):
        compiled = _compile_log_product(formula, parent_html, translation)
    else:
        return _remaining_constrained(
            formula, parent_html, translation, preferred, scale
        )
    return compiled
