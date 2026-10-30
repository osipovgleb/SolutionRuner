"""Read complete trigonometric questions and exact open angular intervals."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from ..triangles.isosceles.planner import _section
from .expression_condition import read_math_markup
from .power_arithmetic import clean
from .trig_angles import parse_angle


@dataclass
class Question:
    condition: dict
    answer: dict | None
    solution: dict | None
    expression: str
    relation: str | None
    domain: str | None


def read_question(context):
    content, condition, formulas, text = read_math_markup(context, indexed=True)
    pattern = r"Найдите(?: значение(?: выражения)?)? \ufff00(?:, если \ufff01(?: и \ufff02)?)?\.?"
    if (
        content.get("assets")
        or condition.get("asset_keys")
        or not re.fullmatch(pattern, text)
        or not 1 <= len(formulas) <= 3
    ):
        raise UnsupportedCondition(
            "a complete text-only trigonometric question is required"
        )
    if len(formulas) != (3 if "\ufff02" in text else 2 if "\ufff01" in text else 1):
        raise UnsupportedCondition("an unparsed trigonometric declaration remains")
    return Question(
        condition,
        _section(content, "answer"),
        _section(content, "solution"),
        formulas[0],
        formulas[1] if len(formulas) > 1 else None,
        formulas[2] if len(formulas) > 2 else None,
    )


def interval(text, variable):
    if text is None:
        return None
    text = clean(text)
    membership = re.fullmatch(re.escape(variable) + r"\\in\((.+);(.+)\)", text)
    inequalities = re.fullmatch(r"(.+)\\lt" + re.escape(variable) + r"\\lt(.+)", text)
    match = membership or inequalities
    if not match:
        raise UnsupportedCondition("an exact open angular interval is required")
    low, high = (parse_angle(match[i])[0] for i in [1, 2])
    if (
        not 0 < high - low <= 2
        or (2 * low).is_Integer is not True
        or (2 * high).is_Integer is not True
    ):
        raise UnsupportedCondition(
            "the angular endpoints must be multiples of half pi within one period"
        )
    return low, high


def allowed(pair, domain):
    if domain is None:
        return True
    sine, cosine = pair
    low, high = domain
    if sine == 0 or cosine == 0:
        axes = {
            (0, 1): sp.Rational(0),
            (1, 0): sp.Rational(1, 2),
            (0, -1): sp.Rational(1),
            (-1, 0): sp.Rational(3, 2),
        }
        point = axes.get((int(sine), int(cosine)))
        return point is not None and any(
            low < point + 2 * k < high
            for k in range(int(low // 2) - 1, int(high // 2) + 2)
        )
    quadrant = {(1, 1): 0, (1, -1): 1, (-1, -1): 2, (-1, 1): 3}.get(
        (sp.sign(sine), sp.sign(cosine))
    )
    if quadrant is None:
        raise UnsupportedCondition("the given exact signs are undecidable")
    return any(k % 4 == quadrant for k in range(int(2 * low), int(2 * high)))


def candidates(function, value, domain):
    if value.is_real is not True or value.free_symbols:
        raise UnsupportedCondition(
            "the given trigonometric value must be an exact real scalar"
        )
    if function in ("sin", "cos"):
        square = sp.simplify(value**2)
        if square.is_Rational is not True or not 0 <= square <= 1:
            raise UnsupportedCondition(
                "the given sine or cosine is outside its exact real range"
            )
        complement = sp.sqrt(1 - square)
        pairs = [
            (value, c) if function == "sin" else (c, value)
            for c in [complement, -complement]
        ]
    else:
        complement = 1 / sp.sqrt(1 + value**2)
        pairs = [
            (value * c, c) if function == "tg" else (c, value * c)
            for c in [complement, -complement]
        ]
    return list(dict.fromkeys(pair for pair in pairs if allowed(pair, domain)))
