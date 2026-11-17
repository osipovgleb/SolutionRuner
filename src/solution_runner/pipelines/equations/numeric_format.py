"""Render exact rational values in mathematical answers."""

from fractions import Fraction

from ..triangles.right.planner import RightTrianglePlanError


def _fraction(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{'-' if value < 0 else ''}\\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def _decimal(value: Fraction) -> str:
    remainder = value.denominator
    twos = fives = 0
    while remainder % 2 == 0:
        remainder //= 2
        twos += 1
    while remainder % 5 == 0:
        remainder //= 5
        fives += 1
    if remainder != 1:
        raise RightTrianglePlanError("result is not a terminating decimal")
    if value.denominator == 1:
        return str(value.numerator)
    digits = max(twos, fives)
    scaled = abs(value.numerator) * 10**digits // value.denominator
    rendered = str(scaled).zfill(digits + 1)
    return f"{'-' if value < 0 else ''}{rendered[:-digits]},{rendered[-digits:]}"
