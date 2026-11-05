"""Read exact positive solid measurements, word factors and explicit pi coefficients."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..equations.power_arithmetic import ScalarParser, rational
from ..probability.common import COUNT, count


def positive(raw, *, words=False, pi=False):
    multiplier = sp.Integer(1)
    if pi:
        match = re.fullmatch(r"(?:(.+?)\s*)?\\pi", raw)
        if match:
            raw, multiplier = match[1] or "1", sp.pi
    if re.search(r"\d\s+\d", raw):
        if re.fullmatch(r"[1-9]\d{0,2}(?: \d{3})+(?:[,.]\d+)?", raw) is None:
            raise ContentPlanError("solid digit groups must be unambiguous thousands")
        raw = raw.replace(" ", "")
    amount = (
        sp.Integer(count(raw))
        if words and re.fullmatch(COUNT, raw)
        else ScalarParser(_decimal_roots(raw)).parse()
    )
    amount *= multiplier
    if (
        amount.is_positive is not True
        or amount.is_real is not True
        or amount.is_finite is not True
    ):
        raise ContentPlanError("solid measurements must be positive finite real values")
    return amount


def sector_fraction(angle, kind):
    angle = positive(str(angle))
    if angle >= 360 or kind not in {"kept", "removed"}:
        raise ContentPlanError("a proper kept or removed sector angle is required")
    return sp.simplify((angle if kind == "kept" else 360 - angle) / 360)


def _decimal_roots(raw):
    def rewrite(match):
        amount = rational(match[1].replace("{,}", ".").replace(",", "."))
        numerator, denominator = amount.as_numer_denom()
        radicand = numerator * denominator
        if radicand > 999999:
            raise ContentPlanError(
                "the solid square root exceeds the supported exact range"
            )
        return r"\sqrt{" + str(radicand) + r"}\cdot\frac{1}{" + str(denominator) + "}"

    return re.sub(r"\\sqrt\{(\d{1,6}(?:\{,\}|[,.])\d{1,6})\}", rewrite, raw)
