"""Exact shared algebra for reciprocal linear equations."""

from __future__ import annotations

from fractions import Fraction


def solve_reciprocal_linear_equation(
    numerator: Fraction,
    coefficient: Fraction,
    constant: Fraction,
    right_side: Fraction,
) -> Fraction:
    """Solve ``numerator / (coefficient*x + constant) = right_side`` exactly."""

    if numerator == 0 or coefficient == 0 or right_side == 0:
        raise ValueError("reciprocal linear equation has a zero essential coefficient")
    root = (numerator / right_side - constant) / coefficient
    if coefficient * root + constant == 0:
        raise ValueError("root violates the denominator domain")
    return root
