"""Read exact positive solid measurements, word factors and explicit pi coefficients."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..equations.power_arithmetic import ScalarParser
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
        else ScalarParser(raw).parse()
    )
    amount *= multiplier
    if (
        amount.is_positive is not True
        or amount.is_real is not True
        or amount.is_finite is not True
    ):
        raise ContentPlanError("solid measurements must be positive finite real values")
    return amount
