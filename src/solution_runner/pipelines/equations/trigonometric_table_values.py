"""Reviewed tabular trigonometric values and their diagrams."""

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class _Value:
    angles: tuple[Fraction, ...]  # coefficients of pi
    period: int
    asset: str


_VALUES: dict[str, dict[str, _Value]] = {
    "cos": {
        "1": _Value((Fraction(0),), 2, "cos-one.svg"),
        "-1": _Value((Fraction(1),), 2, "cos-minus-one.svg"),
        "0": _Value((Fraction(1, 2),), 2, "cos-zero.svg"),
        r"\frac{1}{2}": _Value((Fraction(1, 3), Fraction(-1, 3)), 2, "cos-half.svg"),
        r"-\frac{1}{2}": _Value(
            (Fraction(2, 3), Fraction(-2, 3)), 2, "cos-minus-half.svg"
        ),
        r"\frac{\sqrt{2}}{2}": _Value(
            (Fraction(1, 4), Fraction(-1, 4)), 2, "cos-sqrt2-over-2.svg"
        ),
        r"-\frac{\sqrt{2}}{2}": _Value(
            (Fraction(3, 4), Fraction(-3, 4)), 2, "cos-minus-sqrt2-over-2.svg"
        ),
        r"\frac{\sqrt{3}}{2}": _Value(
            (Fraction(1, 6), Fraction(-1, 6)), 2, "cos-sqrt3-over-2.svg"
        ),
        r"-\frac{\sqrt{3}}{2}": _Value(
            (Fraction(5, 6), Fraction(-5, 6)), 2, "cos-minus-sqrt3-over-2.svg"
        ),
    },
    "sin": {
        "0": _Value((Fraction(0),), 2, "sin-zero.svg"),
        "1": _Value((Fraction(1, 2),), 2, "sin-one.svg"),
        "-1": _Value((Fraction(-1, 2),), 2, "sin-minus-one.svg"),
        r"\frac{1}{2}": _Value((Fraction(1, 6), Fraction(5, 6)), 2, "sin-half.svg"),
        r"-\frac{1}{2}": _Value(
            (Fraction(-1, 6), Fraction(7, 6)), 2, "sin-minus-half.svg"
        ),
        r"\frac{\sqrt{2}}{2}": _Value(
            (Fraction(1, 4), Fraction(3, 4)), 2, "sin-sqrt2-over-2.svg"
        ),
        r"-\frac{\sqrt{2}}{2}": _Value(
            (Fraction(-1, 4), Fraction(5, 4)), 2, "sin-minus-sqrt2-over-2.svg"
        ),
        r"\frac{\sqrt{3}}{2}": _Value(
            (Fraction(1, 3), Fraction(2, 3)), 2, "sin-sqrt3-over-2.svg"
        ),
        r"-\frac{\sqrt{3}}{2}": _Value(
            (Fraction(-1, 3), Fraction(4, 3)), 2, "sin-minus-sqrt3-over-2.svg"
        ),
    },
    "tg": {
        "0": _Value((Fraction(0),), 1, "tg-zero.svg"),
        "1": _Value((Fraction(1, 4),), 1, "tg-one.svg"),
        "-1": _Value((Fraction(-1, 4),), 1, "tg-minus-one.svg"),
        r"\sqrt{3}": _Value((Fraction(1, 3),), 1, "tg-sqrt3.svg"),
        r"-\sqrt{3}": _Value((Fraction(-1, 3),), 1, "tg-minus-sqrt3.svg"),
        r"\frac{1}{\sqrt{3}}": _Value((Fraction(1, 6),), 1, "tg-one-over-sqrt3.svg"),
        r"-\frac{1}{\sqrt{3}}": _Value(
            (Fraction(-1, 6),), 1, "tg-minus-one-over-sqrt3.svg"
        ),
    },
}
