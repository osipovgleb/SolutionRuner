"""Compile early power patterns and general logarithmic products."""

from ..word_problems.common import UnsupportedCondition


def _early_power(formula, parent_html, translation, preferred, scale):
    from .exam_trigonometric_power_absolute import compile_quotient as absolute_power
    from .exam_trigonometric_power_grouping import compile_grouping as power_grouping
    from .exam_trigonometric_power_polynomial import (
        compile_polynomial as power_polynomial,
    )

    compiled = absolute_power(formula, parent_html)
    if compiled is not None:
        if translation or scale != 1:
            raise UnsupportedCondition(
                "absolute power quotients require their original unit angle"
            )
        return compiled
    compiled = power_grouping(formula, parent_html)
    if compiled is not None:
        if translation:
            raise UnsupportedCondition("power grouping requires its original argument")
        return compiled
    compiled = power_polynomial(formula, parent_html)
    if compiled is not None:
        if translation:
            raise UnsupportedCondition(
                "exponential quadratics require their original angle"
            )
        return compiled
    from .exam_trigonometric_power_equality import compile_quotient as power_quotient

    compiled = power_quotient(formula, parent_html, preferred=preferred, scale=scale)
    if compiled is not None:
        if translation:
            raise UnsupportedCondition("power quotients require their original angle")
        return compiled
    return None


def _compile_log_product(formula, parent_html, translation):
    from .exam_trigonometric_log_product import compile_product, prepare

    if translation:
        raise UnsupportedCondition("log products require the original variable")
    from .exam_trigonometric_log_common import quadratic
    from .exam_trigonometric_log_equality import compile_equality, reviewed
    from .exam_trigonometric_log_linear import compile_linear
    from .exam_trigonometric_log_polynomial import compile_polynomial
    from .exam_trigonometric_log_powers import compile_powers
    from .exam_trigonometric_log_powers import reviewed as log_powers
    from .exam_trigonometric_log_variable import compile_variable
    from .exam_trigonometric_log_variable import reviewed as variable_base

    compiled = (
        compile_variable(formula, parent_html)
        if variable_base(formula)
        else compile_powers(formula, parent_html)
        if log_powers(formula)
        else compile_polynomial(formula, parent_html)
        if quadratic(formula)
        else compile_linear(formula, parent_html)
    )
    if compiled is None:
        compiled = (
            compile_equality(formula, parent_html)
            if reviewed(formula)
            else compile_polynomial(formula, parent_html)
        )
    if compiled is None:
        compiled = prepare(compile_product(formula), parent_html)
    return compiled


def _preferred_method(formula, parent_html, scale, translation, options):
    ratio_product, triple_angle, sum_identity, square_sum = options
    if parent_html:
        from .exam_trigonometric_absolute_affine import (
            compile_absolute as affine_absolute,
        )

        compiled = affine_absolute(formula, parent_html)
        if compiled is not None:
            if translation or (
                scale != 1 and (compiled.absolute_affine.common is None or scale != 2)
            ):
                raise UnsupportedCondition(
                    "absolute cases require their reviewed original argument"
                )
            return compiled, None
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
        from .exam_trigonometric_sum_product import compile_square

        if translation:
            raise UnsupportedCondition(
                "sum-to-product methods require the original variable"
            )
        return compile_square(formula), None
    return None


def _remaining_constrained(formula, parent_html, translation, preferred, scale):
    from .exam_trigonometric_global_radical import reviewed as global_radical
    from .exam_trigonometric_original_quotients import reviewed as original_quotient
    from .exam_trigonometric_power_equality import reviewed as positive_powers
    from .exam_trigonometric_radical_equation import variable_radicals
    from .exam_trigonometric_radical_style import kind as radical_kind
    from .exam_trigonometric_strict_quotient import reviewed as strict_quotient
    from .exam_trigonometric_sum_squares import reviewed as sum_squares

    if positive_powers(formula):
        from .exam_trigonometric_power_equality import compile_equality

        if translation:
            raise UnsupportedCondition("positive powers require their original angle")
        compiled = compile_equality(
            formula, parent_html, preferred=preferred, scale=scale
        )
    elif strict_quotient(formula, parent_html):
        from .exam_trigonometric_strict_quotient import compile_quotient

        if translation:
            raise UnsupportedCondition(
                "strict radical denominators require their original physical angle"
            )
        compiled = compile_quotient(formula, parent_html)
    elif original_quotient(formula, parent_html):
        from .exam_trigonometric_original_quotients import compile_quotient

        if translation:
            raise UnsupportedCondition(
                "original quotient poles require the physical angle"
            )
        compiled = compile_quotient(formula, parent_html)
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
            compiled = compile_radical(
                formula, radical_kind(parent_html), parent_html=parent_html
            )
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
