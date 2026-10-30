"""Exact bases and affine exponents shared by elementary equation rules."""

from __future__ import annotations

import re
from fractions import Fraction

from solution_runner.pipelines.core.numbers import (
    NumberFormatError,
    format_answer,
    format_latex_fraction,
    parse_rational,
)

_NUMBER = r"(?:[1-9]\d*(?:\{,\}\d+)?|0\{,\}[1-9]\d*|\\frac\{[1-9]\d*\}\{[1-9]\d*\}|\(\\frac\{[1-9]\d*\}\{[1-9]\d*\}\)|\\left\(\\frac\{[1-9]\d*\}\{[1-9]\d*\}\\right\))"
_EXPONENT = r"(?:[^{}]|\{,\})+"
_FORMULA = re.compile(
    rf"(?P<base>{_NUMBER})\^\{{(?P<exponent>{_EXPONENT})\}}=(?P<right>{_NUMBER})"
)
_TWO_BASES = re.compile(
    rf"(?P<left_base>{_NUMBER})\^\{{(?P<left_exponent>{_EXPONENT})\}}=(?P<right_base>{_NUMBER})\^\{{(?P<right_exponent>{_EXPONENT})\}}"
)
_SCALED_POWER = re.compile(
    rf"(?P<factor>{_NUMBER})\\cdot (?P<base>{_NUMBER})\^\{{(?P<exponent>{_EXPONENT})\}}=(?P<right>.+)"
)
_POWER_DIFFERENCE = re.compile(
    rf"(?P<base>{_NUMBER})\^\{{(?P<left_exponent>{_EXPONENT})\}}-(?P=base)\^\{{(?P<right_exponent>{_EXPONENT})\}}=(?P<right>{_NUMBER})"
)
_DIVIDED_SAME_BASE = re.compile(
    rf"(?P<base>{_NUMBER})\^\{{(?P<left_exponent>[^{{}}]+)\}}\\colon (?P=base)\^\{{(?P<right_exponent>[^{{}}]+)\}}=(?P<right>{_NUMBER})"
)
_MULTIPLIED_SAME_BASE = re.compile(
    rf"(?P<base>{_NUMBER})\^\{{(?P<left_exponent>[^{{}}]+)\}}\\cdot (?P=base)\^\{{(?P<right_exponent>[^{{}}]+)\}}=(?P<right>{_NUMBER})"
)
_CONSTANT_FIRST = re.compile(r"(?P<constant>-?\d+)(?P<sign>[+-])(?P<coefficient>\d*)x")
_VARIABLE_FIRST = re.compile(r"(?P<coefficient>-?\d*)x(?P<sign>[+-])(?P<constant>\d+)")


class UnsupportedCondition(ValueError):
    pass


def _parse_base(token: str) -> Fraction:
    """Parse a supported base, including TeX sizing delimiters around a fraction."""
    return parse_rational(
        token.replace(r"\left(", "").replace(r"\right)", "").strip("()")
    )


def _exponent(value: Fraction, base: Fraction) -> int:
    if base <= 0 or base == 1:
        raise UnsupportedCondition("base must be positive and different from one")
    if value <= 0:
        raise UnsupportedCondition("right side must be positive")
    exponent = 0
    current = Fraction(1)
    if (base > 1 and value > 1) or (base < 1 and value < 1):
        while (base > 1 and current < value) or (base < 1 and current > value):
            current *= base
            exponent += 1
    elif value != 1:
        while (base > 1 and current > value) or (base < 1 and current < value):
            current /= base
            exponent -= 1
    if current != value:
        raise UnsupportedCondition("right side is not an exact power of the base")
    return exponent


def _parse_linear(value: str) -> tuple[int, int]:
    if value == "x":
        return 0, 1
    if value == "-x":
        return 0, -1
    if re.fullmatch(r"-?\d+x", value):
        return 0, int(value[:-1])
    m = _CONSTANT_FIRST.fullmatch(value)
    if m:
        coefficient = int(m.group("coefficient") or "1") * (
            -1 if m.group("sign") == "-" else 1
        )
        return int(m.group("constant")), coefficient
    m = _VARIABLE_FIRST.fullmatch(value)
    if m:
        constant = int(m.group("constant")) * (-1 if m.group("sign") == "-" else 1)
        coefficient = (
            -1 if m.group("coefficient") == "-" else int(m.group("coefficient") or "1")
        )
        return constant, coefficient
    raise UnsupportedCondition("exponent is not an accepted affine expression")


def _linear_latex(constant: int, coefficient: int) -> str:
    x = (
        "x"
        if coefficient == 1
        else "-x"
        if coefficient == -1
        else f"{format_latex_fraction(Fraction(coefficient))}x"
    )
    if constant == 0:
        return x
    return f"{format_latex_fraction(Fraction(constant))}{'+' if coefficient > 0 else ''}{x}"


def _variable_first_latex(constant: int, coefficient: int) -> str:
    """Render a nonzero affine exponent in the familiar ``mx ± n`` order."""
    x = (
        "x"
        if coefficient == 1
        else "-x"
        if coefficient == -1
        else f"{format_latex_fraction(Fraction(coefficient))}x"
    )
    return (
        x
        if constant == 0
        else f"{x}{'+' if constant > 0 else ''}{format_latex_fraction(Fraction(constant))}"
    )


def _parse_exponent(value: str) -> tuple[Fraction | int, Fraction | int]:
    if "{,}" not in value:
        constant, coefficient = _parse_linear(value)
        return constant, coefficient
    number = r"\d+(?:\{,\}\d+)?"
    variable_first = re.fullmatch(
        rf"(?P<coefficient>[+-]?(?:{number})?)x(?P<constant>[+-]{number})?", value
    )
    constant_first = re.fullmatch(
        rf"(?P<constant>[+-]?{number})(?P<coefficient>[+-](?:{number})?)x", value
    )
    match = variable_first or constant_first
    if match is None:
        raise UnsupportedCondition(
            "exponent is not an accepted rational affine expression"
        )
    coefficient = match["coefficient"]
    coefficient = (
        "1" if coefficient in ("", "+") else "-1" if coefficient == "-" else coefficient
    )
    return parse_rational(match["constant"] or "0"), parse_rational(coefficient)


def _base_latex(value: Fraction) -> str:
    latex = format_latex_fraction(value)
    return latex if value.denominator == 1 else f"({latex})"


def _answer_steps(value: Fraction) -> str:
    """Render the terminal answer in exact and, when needed, decimal form."""
    exact = format_latex_fraction(value)
    if value.denominator == 1:
        return f"x={exact}"
    try:
        decimal = format_answer(value)
    except NumberFormatError as e:
        raise UnsupportedCondition("answer does not terminate") from e
    return f"x={exact}\\iff x={decimal.replace(',', '{,}')}"


def _primitive_integer_base(base: Fraction) -> tuple[Fraction, int]:
    if base.numerator == 1 and base.denominator > 1:
        value = base.denominator
        for candidate in range(2, value):
            power = 1
            degree = 0
            while power < value:
                power *= candidate
                degree += 1
            if power == value:
                return Fraction(candidate), -degree
        return base, 1
    if base.denominator != 1:
        return base, 1
    value = base.numerator
    for candidate in range(2, value):
        power = 1
        degree = 0
        while power < value:
            power *= candidate
            degree += 1
        if power == value:
            return Fraction(candidate), degree
    return base, 1


def _common_base_for_two_sides(base: Fraction) -> tuple[Fraction, int]:
    """Express a unit fraction through its positive reciprocal base."""
    if base.numerator == 1 and base.denominator > 1:
        common, degree = _primitive_integer_base(Fraction(base.denominator))
        return common, -degree
    return _primitive_integer_base(base)


def _fractional_common_base(base: Fraction) -> tuple[Fraction, int]:
    """Reduce a unit fraction while keeping the common base fractional."""
    if base.numerator != 1 or base.denominator <= 1:
        return base, 1
    denominator_base, degree = _primitive_integer_base(Fraction(base.denominator))
    if denominator_base.denominator != 1:
        return base, 1
    return Fraction(1, denominator_base.numerator), degree


def _scaled_exponent(source: str, factor: int) -> str:
    constant, coefficient = _parse_exponent(source)
    m = _VARIABLE_FIRST.fullmatch(source)
    if m:
        coefficient *= factor
        constant *= factor
        if factor == -1 and coefficient < 0 and constant > 0:
            term = "x" if coefficient == -1 else f"{-coefficient}x"
            return f"{constant}-{term}"
        x = (
            "x"
            if coefficient == 1
            else "-x"
            if coefficient == -1
            else f"{coefficient}x"
        )
        return x if constant == 0 else f"{x}{constant:+d}"
    return _linear_latex(constant * factor, coefficient * factor)
