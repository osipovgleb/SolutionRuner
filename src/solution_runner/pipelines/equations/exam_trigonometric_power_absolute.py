"""Cancel a unit trig factor only when its zeros violate the original domain."""

import re

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_absolute import R, RootPlaceholderParser
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_methods import Equation, ExamAngleParser
from .exam_trigonometric_power_equality import (
    PowerEquality,
    common_exponent,
    parent_equations,
    parent_forms,
    positive_pair,
    prime_logs,
    reviewed,
)
from .exam_trigonometric_power_parser import PositivePowerParser
from .exam_trigonometric_radical_equation import compile_values
from .power_arithmetic import clean


class AbsolutePowerParser(PositivePowerParser, RootPlaceholderParser):
    extra_symbols = (R,)


def source(text, radicand_text):
    text = clean(text)
    plain = re.sub(r"\\[A-Za-z]+", "", text).replace("x", "")
    if re.search("[A-Za-z]", plain) or text.count("|") != 2 or r"\alpha" in text:
        raise UnsupportedCondition(
            "one absolute exponent in the original variable x is required"
        )
    start, end = text.index("|"), text.rindex("|")
    atoms, denominators = {}, []
    variable = (
        ExamAngleParser(
            text[start + 1 : end].replace("x", r"\alpha"), atoms, denominators
        )
        .parse()
        .value
    )
    body = text[:start] + "(r)" + text[end + 1 :]
    expression = (
        AbsolutePowerParser(body.replace("x", r"\alpha"), atoms, denominators)
        .parse()
        .value
    )
    radicand = (
        ExamAngleParser(radicand_text.replace("x", r"\alpha"), atoms, denominators)
        .parse()
        .value
    )
    if not atoms or any(
        a.variable != r"\alpha" or a.coefficient != 1 or a.shift != 0
        for a in atoms.values()
    ):
        raise UnsupportedCondition(
            "original unit unshifted trig arguments are required"
        )
    (expression, variable, radicand), poles, identities = compile_values(
        [expression, variable, radicand], atoms, denominators
    )
    if variable not in (S, C):
        raise UnsupportedCondition("one absolute unit sine or cosine is required")
    values, divisor = positive_pair(expression)
    left, right = (prime_logs(v) for v in values)
    base, exponent = common_exponent(left, right, extra_symbols=(R,))
    canceled = C if variable == S else S
    linear = sp.cancel(exponent / canceled)
    if (
        not linear.is_polynomial(R)
        or sp.degree(linear, R) != 1
        or any(v.free_symbols for v in sp.Poly(linear, R).all_coeffs())
    ):
        raise UnsupportedCondition(
            "one linear absolute level times the other unit trig factor is required"
        )
    level = sp.simplify(-linear.subs(R, 0) / linear.coeff(R))
    if level.free_symbols or level.is_real is not True or not 0 <= level <= 1:
        raise UnsupportedCondition(
            "one nonnegative absolute level within the unit range is required"
        )
    from .exam_trigonometric_power_style import equal_sides

    replacement = {R: sp.Abs(variable)}
    values = tuple(v.xreplace(replacement) for v in values)
    left, right = (
        {p: e.xreplace(replacement) for p, e in v.items()} for v in (left, right)
    )
    data = PowerEquality(
        *values,
        tuple(sorted(left.items())),
        tuple(sorted(right.items())),
        base,
        exponent.xreplace(replacement),
        equal_sides(left, right, base, base),
        radicand,
        radicand_text,
        divisor,
        absolute_level=(variable, canceled, level),
    )
    numerator, denominator = sp.fraction(radicand)
    return Equation(
        variable**2 - level**2,
        identities,
        sp.S.One,
        poles=poles,
        domain=sp.expand(numerator * denominator),
        strict_domain=True,
        power_equality=data,
    )


def compile_quotient(formula, parent_html):
    from .exam_trigonometric_power_polynomial import validate_radicand
    from .exam_trigonometric_strict_quotient import operands

    text = clean(formula)
    if "|" not in text or not reviewed(text):
        return None
    parts = operands(text)
    if parts is None:
        return None
    compiled = source(*parts)
    data = compiled.power_equality
    variable, canceled, _ = data.absolute_level
    validate_radicand(data.radicand, rational_domain=True)
    if any(p not in (S, C) for p in compiled.poles):
        raise UnsupportedCondition("original unit trig poles are required")
    phases = (0, 1) if canceled == S else (sp.Rational(1, 2), sp.Rational(3, 2))
    for q in phases:
        substitution = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
        if not (
            any(sp.simplify(p.subs(substitution)) == 0 for p in compiled.poles)
            or sp.simplify(compiled.domain.subs(substitution)).is_nonpositive is True
        ):
            raise UnsupportedCondition(
                "the canceled trig factor can vanish in the original domain"
            )
    certified_parent = False
    for equation in parent_equations(parent_forms(parent_html)):
        if "|" not in equation:
            continue
        first, second = equation.split("=")
        try:
            prototype = source("(" + first + ")-(" + second + ")", "1")
        except UnsupportedCondition:
            continue
        if prototype.power_equality.absolute_level[:2] == (variable, canceled):
            certified_parent = True
            break
    if not certified_parent:
        raise UnsupportedCondition(
            "the parent must retain the complete absolute positive-power method"
        )
    return compiled
