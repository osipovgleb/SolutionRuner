"""Render exact trigonometric table solution expressions."""

from fractions import Fraction

from solution_runner.pipelines.core.numbers import format_answer


def _table_number(value: Fraction) -> str:
    """Prefer the decimal-comma form in substitutions and the selected root."""
    return format_answer(value, allow_latex_fraction=True).replace(",", "{,}")


def _pi_fraction(value: Fraction) -> str:
    """Render a multiple of π with π inside the numerator."""
    if value == 0:
        return "0"
    sign = "-" if value < 0 else ""
    numerator = abs(value.numerator)
    if value.denominator == 1:
        return f"{sign}{'' if numerator == 1 else numerator}\\pi"
    top = r"\pi" if numerator == 1 else rf"{numerator}\pi"
    return rf"{sign}\frac{{{top}}}{{{value.denominator}}}"


def _union(lines: list[str]) -> str:
    """Render one equation or a visible совокупность with one parameter k."""
    if len(lines) == 1:
        return lines[0] + r",\quad k\in\mathbb Z"
    return (
        r"\left[\begin{aligned}"
        + r"\\".join(lines)
        + r"\end{aligned}\right.,\quad k\in\mathbb Z"
    )


def _ceil(value: Fraction) -> int:
    return -((-value.numerator) // value.denominator)
