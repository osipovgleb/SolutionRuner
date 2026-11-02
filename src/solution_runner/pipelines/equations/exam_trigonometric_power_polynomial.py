"""Keep a positive exponential quadratic and all original denominator domains."""

from dataclasses import dataclass
from functools import cmp_to_key

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_trigonometric_compile import C, S, T, U
from .exam_trigonometric_methods import Equation
from .exam_trigonometric_power_equality import prime_logs, reviewed
from .exam_trigonometric_power_parser import PositivePowerParser
from .exam_trigonometric_power_polynomial_style import (
    PolynomialStyle,
    UnitShape,
    compare_roots,
    review,
    shapes,
)
from .exam_trigonometric_power_units import E, PowerUnit, normalize
from .exam_trigonometric_radical_equation import compile_values, trig_polynomial
from .logarithm_arithmetic import actual, log_ratio
from .power_arithmetic import balanced, clean


@dataclass(frozen=True)
class PowerPolynomial:
    unit: PowerUnit
    shape: UnitShape
    style: PolynomialStyle
    powers: tuple
    levels: tuple
    multiplier: sp.Rational
    wrapper: str | None
    strict_root: bool
    log_denominator: tuple | None = None


def unwrap(formula):
    text = clean(formula).removesuffix(".")
    if text.count("=") != 1:
        raise UnsupportedCondition("one complete exponential quadratic is required")
    wrapper = None
    if text.startswith(r"\frac{") and text.endswith("=0"):
        numerator, end = balanced(text, 5)
        denominator, stop = balanced(text, end)
        if stop == len(text) - 2:
            text, wrapper = numerator + "=0", denominator
    return text, wrapper


def source(formula, *, rational_domain=False):
    text, wrapper = unwrap(formula)
    atoms, denominators = {}, []
    nodes = [
        PositivePowerParser(v.replace("x", r"\alpha"), atoms, denominators).parse()
        for v in text.split("=")
    ]
    strict = wrapper is not None and wrapper.startswith(r"\sqrt{")
    if wrapper is not None:
        operand = wrapper
        if strict:
            operand, end = balanced(wrapper, 5)
            if end != len(wrapper):
                raise UnsupportedCondition(
                    "the whole radical denominator must be retained"
                )
        nodes.append(
            PositivePowerParser(
                operand.replace("x", r"\alpha"), atoms, denominators
            ).parse()
        )
    if not atoms or any(a.variable != r"\alpha" for a in atoms.values()):
        raise UnsupportedCondition("all original power arguments must use x")
    values, poles, identities = compile_values(
        [n.value for n in nodes], atoms, denominators
    )
    domain = values[2] if strict else None
    if domain is not None:
        validate_radicand(domain, rational_domain=rational_domain)
    poles = (*poles, *((values[2],) if wrapper is not None and not strict else ()))
    retained = []
    for pole in poles:
        if not pole.free_symbols:
            if pole == 0:
                raise UnsupportedCondition(
                    "an original denominator is identically zero"
                )
            continue
        try:
            prime_logs(pole)
        except UnsupportedCondition:
            if not pole.is_polynomial(S, C) or sp.Poly(pole, S, C).total_degree() > 2:
                raise UnsupportedCondition(
                    "all original trig poles must remain bounded polynomials"
                ) from None
            retained.append(sp.cancel(pole / sp.Poly(pole, S, C).LC()))
    return (
        values[0] - values[1],
        tuple(dict.fromkeys(retained)),
        identities,
        domain,
        wrapper,
        strict,
    )


def validate_radicand(domain, *, rational_domain=False):
    if not domain.is_polynomial(S, C) or sp.Poly(domain, S, C).total_degree() > 2:
        numerator, denominator = sp.fraction(domain)
        weights = [sp.cancel(denominator / variable) for variable in (S, C)]
        if (
            not rational_domain
            or not numerator.is_polynomial(S, C)
            or sp.Poly(numerator, S, C).total_degree() > 1
            or not any(
                not w.free_symbols and w.is_real is True and w != 0 for w in weights
            )
        ):
            raise UnsupportedCondition("a bounded whole quadratic radicand is required")


def polynomial_source(formula):
    from .exam_trigonometric_radical_equation import variable_radicals

    text, _ = unwrap(formula)
    if variable_radicals(text):
        return None
    if r"\log" not in formula:
        return (*source(formula), None)
    text, wrapper = unwrap(formula)
    if wrapper is None or r"\log" in text:
        return None
    from .exam_trigonometric_log_common import parse_expression
    from .exam_trigonometric_radical_equation import same

    parsed = parse_expression(wrapper + "=0")
    if parsed is None:
        return None
    nodes, logs, constants, compiled, _ = parsed
    if len(logs) != 1 or constants or nodes[0].value != logs[0][0]:
        raise UnsupportedCondition(
            "one complete fixed-base logarithm denominator is required"
        )
    values, original_poles, log_identities = compiled
    argument = values[1]
    validate_radicand(argument, rational_domain=True)
    if same(argument, sp.S.One) or same(argument, sp.S.Zero):
        raise UnsupportedCondition(
            "the original log denominator is undefined or identically zero"
        )
    numerator, denominator = sp.fraction(argument)
    expression, poles, identities, _, _, _ = source(text)
    retained = []
    for pole in (*poles, *original_poles, sp.expand(numerator - denominator)):
        if (
            same(pole, sp.S.Zero)
            or not pole.is_polynomial(S, C)
            or sp.Poly(pole, S, C).total_degree() > 2
        ):
            raise UnsupportedCondition(
                "all original log-denominator poles must remain bounded nonzero polynomials"
            )
        if pole.free_symbols:
            retained.append(sp.cancel(pole / sp.Poly(pole, S, C).LC()))
    return (
        expression,
        tuple(dict.fromkeys(retained)),
        tuple(dict.fromkeys((*identities, *log_identities))),
        sp.expand(numerator * denominator),
        wrapper,
        True,
        (logs[0][1], argument),
    )


def compile_polynomial(formula, parent_html):
    if not reviewed(formula):
        return None
    if r"\log" in formula:
        text, wrapper = unwrap(formula)
        if wrapper is None or not wrapper.startswith(r"\log_") or r"\log" in text:
            return None
    from bs4 import BeautifulSoup

    if (
        "два случая"
        in BeautifulSoup(parent_html, "html.parser")
        .get_text(" ")
        .replace("\xad", "")
        .lower()
    ):
        return None
    style = review(parent_html)
    if style is None:
        return None
    parsed = polynomial_source(formula)
    if parsed is None:
        return None
    expression, poles, identities, domain, wrapper, strict, log_denominator = parsed
    unit = None
    for shape in shapes(style, formula):
        unit = normalize(
            expression,
            shape.argument,
            below_one=style.below_one,
            exponent_multiplier=style.exponent_multiplier,
        )
        if unit is not None:
            break
    if unit is None:
        raise UnsupportedCondition(
            "the complete equation needs one certified positive quadratic unit"
        )
    if shape.scale != 1 and (poles or domain is not None):
        raise UnsupportedCondition(
            "scaled power domains require a separate original-angle certificate"
        )
    canonical = (
        (S / C if shape.variable == T else C / S)
        if shape.variable in (T, U)
        else trig_polynomial(
            "sin" if shape.variable == S else "cos", sp.Rational(shape.scale)
        )
    )
    multiplier = sp.cancel(unit.argument / canonical**shape.power)
    if multiplier.is_Rational is not True or multiplier == 0:
        raise UnsupportedCondition(
            "a rational multiple of one reviewed trig power is required"
        )
    powers, levels = power_levels(unit, style.ascending)
    data = PowerPolynomial(
        unit,
        shape,
        style,
        powers,
        levels,
        multiplier,
        wrapper,
        strict and log_denominator is None,
        log_denominator,
    )
    raw = sp.prod(
        shape.variable**shape.power - level / multiplier
        for level in levels
        if level is not None
    )
    return Equation(
        sp.expand(raw),
        identities,
        sp.Rational(shape.scale),
        poles,
        domain=domain,
        strict_domain=strict,
        power_polynomial=data,
    )


def power_levels(unit, ascending):
    powers = tuple(
        sorted(
            roots(unit.polynomial.subs(E, X)),
            key=cmp_to_key(compare_roots),
            reverse=not ascending,
        )
    )
    levels = []
    for value in powers:
        if compare_roots(value, sp.S.Zero) <= 0:
            levels.append(None)
            continue
        level = actual(log_ratio(unit.base, value))
        if level.is_Rational is not True or abs(level) > 100 or level.q > 100:
            raise UnsupportedCondition(
                "bounded rational exponential levels are required"
            )
        levels.append(level)
    return powers, tuple(levels)
