"""Format exact numerical and trigonometric values for triangle solutions."""

from __future__ import annotations

import math
import re
from fractions import Fraction

from solution_runner.pipelines.core.errors import (
    ContentPlanError as RightTrianglePlanError,
)


def _trig_square(value: str) -> Fraction:
    """Parse one squared trig value from supported exact LaTeX forms."""

    fraction = re.fullmatch(r"\\frac\{(\d+)\}\{(\d+)\}", value)
    if fraction is not None:
        parsed = Fraction(int(fraction.group(1)), int(fraction.group(2)))
        return parsed * parsed
    decimal = re.fullmatch(r"(\d+)\{,\}(\d+)", value)
    if decimal is not None:
        parsed = Fraction(f"{decimal.group(1)}.{decimal.group(2)}")
        return parsed * parsed
    denominator_radical = re.fullmatch(
        r"\\frac\{(\d+)\}\{(?:(\d+))?\\sqrt\{(\d+)\}\}",
        value,
    )
    if denominator_radical is not None:
        numerator = int(denominator_radical.group(1))
        coefficient = int(denominator_radical.group(2) or "1")
        radicand = int(denominator_radical.group(3))
        return Fraction(
            numerator * numerator,
            coefficient * coefficient * radicand,
        )
    radical = re.fullmatch(
        r"\\frac\{(?:(\d+))?\\sqrt\{(\d+)\}\}\{(\d+)\}",
        value,
    )
    if radical is not None:
        coefficient = int(radical.group(1) or "1")
        return Fraction(
            coefficient * coefficient * int(radical.group(2)),
            int(radical.group(3)) ** 2,
        )
    raise RightTrianglePlanError(
        "sin A or cos A must be rational or a square-root fraction"
    )


def _fraction_latex(value: Fraction) -> str:
    """Render one reduced rational value as an ordinary LaTeX fraction."""

    return rf"\frac{{{value.numerator}}}{{{value.denominator}}}"


def _positive_root_latex(square: Fraction) -> str:
    """Render the positive root of one exact rational square."""

    numerator = square.numerator
    denominator = square.denominator
    root_numerator = math.isqrt(numerator)
    root_denominator = math.isqrt(denominator)
    if (
        root_numerator * root_numerator == numerator
        and root_denominator * root_denominator == denominator
    ):
        reduced = Fraction(root_numerator, root_denominator)
        return rf"\frac{{{reduced.numerator}}}{{{reduced.denominator}}}"
    if root_denominator * root_denominator == denominator:
        square_factor = math.isqrt(numerator)
        while square_factor > 1 and numerator % (square_factor * square_factor):
            square_factor -= 1
        remainder = numerator // (square_factor * square_factor)
        radical = (
            str(square_factor)
            if remainder == 1
            else ("" if square_factor == 1 else str(square_factor))
            + rf"\sqrt{{{remainder}}}"
        )
        return (
            radical
            if root_denominator == 1
            else rf"\frac{{{radical}}}{{{root_denominator}}}"
        )
    radicand = numerator * denominator
    root = math.isqrt(radicand)
    if root * root == radicand:
        reduced = Fraction(root, denominator)
        return rf"\frac{{{reduced.numerator}}}{{{reduced.denominator}}}"
    square_factor = root
    while square_factor > 1 and radicand % (square_factor * square_factor):
        square_factor -= 1
    remainder = radicand // (square_factor * square_factor)
    common = math.gcd(square_factor, denominator)
    coefficient = square_factor // common
    reduced_denominator = denominator // common
    radical = ("" if coefficient == 1 else str(coefficient)) + rf"\sqrt{{{remainder}}}"
    return (
        radical
        if reduced_denominator == 1
        else rf"\frac{{{radical}}}{{{reduced_denominator}}}"
    )


def _canonical_trig_latex(value: str) -> str:
    """Return a reduced fraction for rational trig values and preserve radicals."""

    fraction = re.fullmatch(r"\\frac\{(\d+)\}\{(\d+)\}", value)
    if fraction is not None:
        return _fraction_latex(Fraction(int(fraction.group(1)), int(fraction.group(2))))
    decimal = re.fullmatch(r"(\d+)\{,\}(\d+)", value)
    if decimal is not None:
        return _fraction_latex(
            Fraction(
                int(decimal.group(1) + decimal.group(2)),
                10 ** len(decimal.group(2)),
            )
        )
    return value


def _decimal_reduction_latex(trig_name: str, value: str) -> str | None:
    """Render the required decimal-to-reduced-fraction row when applicable."""

    decimal = re.fullmatch(r"(\d+)\{,\}(\d+)", value)
    if decimal is None:
        return None
    numerator = int(decimal.group(1) + decimal.group(2))
    denominator = 10 ** len(decimal.group(2))
    reduced = _fraction_latex(Fraction(numerator, denominator))
    return (
        rf"\{trig_name} A={value}="
        rf"\frac{{{numerator}}}{{{denominator}}}={reduced}"
    )


def _numeric_latex(value: str) -> float:
    """Evaluate the limited positive-number LaTeX subset used for AC."""

    compact = value.replace(" ", "")
    root = re.fullmatch(r"(?:(\d+(?:\{,\}\d+)?)?)\\sqrt\{(\d+)\}", compact)
    if root is not None:
        coefficient = root.group(1) or "1"
        return float(coefficient.replace("{,}", ".")) * math.sqrt(int(root.group(2)))
    return float(compact.replace("{,}", "."))


def _numeric_square_latex(value: str) -> Fraction:
    """Evaluate the exact square of one supported positive side length."""

    compact = value.replace(" ", "")
    radical = re.fullmatch(r"(?:(\d+(?:\{,\}\d+)?)?)\\sqrt\{(\d+)\}", compact)
    if radical is not None:
        coefficient = Fraction((radical.group(1) or "1").replace("{,}", "."))
        return coefficient * coefficient * int(radical.group(2))
    parsed = Fraction(compact.replace("{,}", "."))
    return parsed * parsed


def _answer_text(value: float) -> str:
    """Format a finite deterministic result for the Russian answer field."""

    rounded = round(value, 10)
    if math.isclose(rounded, round(rounded), abs_tol=1e-9):
        return str(round(rounded))
    return f"{rounded:.10f}".rstrip("0").rstrip(".").replace(".", ",")


def _number_latex(value: Fraction) -> str:
    """Render one exact nonnegative rational without an unnecessary denominator."""

    if value.denominator == 1:
        return str(value.numerator)
    return _fraction_latex(value)


def _positive_root_number_latex(square: Fraction) -> str:
    """Render a positive root and collapse the legacy integer-over-one form."""

    rendered = _positive_root_latex(square)
    unit_fraction = re.fullmatch(r"\\frac\{(\d+)\}\{1\}", rendered)
    return unit_fraction.group(1) if unit_fraction is not None else rendered
