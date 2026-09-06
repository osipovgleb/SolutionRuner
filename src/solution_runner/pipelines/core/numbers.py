"""Exact numeric parsing and rendering shared by deterministic runners."""

from __future__ import annotations

from fractions import Fraction
from math import isqrt
import re


class NumberFormatError(ValueError):
    """Reject a number outside the explicitly supported exact grammar."""


_INTEGER = re.compile(r"[+-]?\d+")
_FRACTION = re.compile(
    r"(?P<sign>[+-]?)\\frac\{(?P<numerator>\d+)\}\{(?P<denominator>[1-9]\d*)\}"
)


def parse_rational(value: str) -> Fraction:
    """Parse one exact integer, decimal-comma/dot, or simple LaTeX fraction."""

    token = value.strip().replace(" ", "")
    if _INTEGER.fullmatch(token):
        return Fraction(int(token), 1)
    match = _FRACTION.fullmatch(token)
    if match is not None:
        result = Fraction(int(match["numerator"]), int(match["denominator"]))
        return -result if match["sign"] == "-" else result
    normalized = token.replace("{,}", ".").replace(",", ".")
    if re.fullmatch(r"[+-]?\d+\.\d+", normalized):
        return Fraction(normalized)
    raise NumberFormatError(f"unsupported exact number: {value!r}")


def terminating_decimal_places(value: Fraction) -> int | None:
    """Return required decimal places, or None for a repeating decimal."""

    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        denominator //= 2
        twos += 1
    while denominator % 5 == 0:
        denominator //= 5
        fives += 1
    return max(twos, fives) if denominator == 1 else None


def format_answer(value: Fraction, *, allow_latex_fraction: bool = False) -> str:
    """Render an exact platform answer using integer or decimal comma notation."""

    if value.denominator == 1:
        return str(value.numerator)
    places = terminating_decimal_places(value)
    if places is None:
        if allow_latex_fraction:
            return format_latex_fraction(value)
        raise NumberFormatError("answer has a non-terminating decimal representation")
    sign = "-" if value < 0 else ""
    numerator = abs(value.numerator) * 10**places // value.denominator
    digits = str(numerator).zfill(places + 1)
    return f"{sign}{digits[:-places]},{digits[-places:]}"


def format_latex_fraction(value: Fraction) -> str:
    """Render a reduced Fraction as compact LaTeX."""

    if value.denominator == 1:
        return str(value.numerator)
    sign = "-" if value < 0 else ""
    return rf"{sign}\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def exact_integer_root(value: int, degree: int) -> int:
    """Return an exact integer root or reject a non-perfect power."""

    if degree <= 0 or value < 0 and degree % 2 == 0:
        raise NumberFormatError("integer root is not real in the supported grammar")
    sign = -1 if value < 0 else 1
    magnitude = abs(value)
    if degree == 2:
        root = isqrt(magnitude)
        if root * root == magnitude:
            return sign * root
        raise NumberFormatError("value is not a perfect square")
    low, high = 0, max(1, magnitude)
    while low <= high:
        middle = (low + high) // 2
        powered = middle**degree
        if powered == magnitude:
            return sign * middle
        if powered < magnitude:
            low = middle + 1
        else:
            high = middle - 1
    raise NumberFormatError("value is not a perfect power")
