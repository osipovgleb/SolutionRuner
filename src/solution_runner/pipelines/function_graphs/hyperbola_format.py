"""Parse and display exact numeric values in graph solutions."""

import re
from fractions import Fraction
from html import escape

from ..core.errors import ContentPlanError


def number(raw: str) -> Fraction:
    raw = raw.strip().replace("−", "-").replace("{,}", ".").replace(",", ".")
    mixed = re.fullmatch(r"(-?\d+)\\frac\{(\d+)\}\{(\d+)\}", raw)
    if mixed:
        whole, numerator, denominator = map(int, mixed.groups())
        if not denominator:
            raise ContentPlanError("zero denominator")
        return Fraction(whole) + (1 if whole >= 0 else -1) * Fraction(
            numerator, denominator
        )
    match = re.fullmatch(r"\\frac\{(-?\d+)\}\{(\d+)\}", raw)
    if match:
        if int(match[2]) == 0:
            raise ContentPlanError("zero denominator")
        return Fraction(int(match[1]), int(match[2]))
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
        raise ContentPlanError("unsupported numeric argument")
    return Fraction(raw)


def latex(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return (
        "-" if value < 0 else ""
    ) + rf"\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def answer_text(value: Fraction) -> str:
    denominator = value.denominator
    for factor in (2, 5):
        while denominator % factor == 0:
            denominator //= factor
    if denominator != 1:
        raise ContentPlanError("answer is not a terminating decimal")
    from decimal import Decimal, localcontext

    with localcontext() as ctx:
        ctx.prec = max(
            30, len(str(abs(value.numerator))) + len(str(value.denominator)) + 5
        )
        return (
            format(Decimal(value.numerator) / Decimal(value.denominator), "f")
            .rstrip("0")
            .rstrip(".")
            if value.denominator != 1
            else str(value.numerator)
        )


def formula(value: str) -> str:
    return f'<span data-inline-latex="{escape(value, quote=True)}"></span>'


def row(value: str) -> str:
    return (
        "<center><p>"
        + formula(value).replace(
            "data-inline-latex=",
            'data-formula-render-mode="display" data-inline-latex=',
        )
        + "</p></center>"
    )
