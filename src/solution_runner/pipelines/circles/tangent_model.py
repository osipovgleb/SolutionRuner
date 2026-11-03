"""Exact reviewed chord lengths and angles involving tangents and a centre secant."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from ..triangles.right.altitude_input import _text
from ..triangles.right.altitude_solver import AltitudeSolveError, _parse_positive_value
from .angle_model import DEGREE, END

RULES = {
    "circle-chord-thirty-radius": "chord_thirty",
    "circle-chord-obtuse-radius": "chord_obtuse",
    "circle-chord-arc-ratio-inscribed": "arc_ratio",
    "circle-tangent-chord-angle-from-arc": "tangent_chord",
    "circle-central-angle-from-tangent-base": "central_from_tangent",
    "circle-two-tangents-angle-from-arc": "two_tangents_angle",
    "circle-two-tangents-arc-from-angle": "two_tangents_arc",
    "circle-tangent-centre-near-angle": "near_angle",
    "circle-tangent-centre-near-arc": "near_arc",
    "circle-tangent-centre-far-angle": "far_angle",
    "circle-tangent-centre-far-arc": "far_arc",
}
PREFIX = r"Найдите угол ACO\s*,\s*если его сторона CA\s+касается окружности, O\s*[—–-]\s*центр окружности,\s*"
PATTERNS = (
    (
        "chord",
        rf"Найдите хорду, на которую опирается угол\s+(.+?)\s*{DEGREE}\s*,\s*вписанный в окружность радиуса\s+(.+?)\s*\.",
    ),
    (
        "arc_ratio",
        r"Хорда AB\s+делит окружность на две части, градусные величины которых относятся как\s+(.+?)\s*(?::|\\colon)\s*(.+?)\s*\.\s*Под каким углом видна эта хорда из точки C\s*,\s*принадлежащей меньшей дуге окружности\s*\?\s*Ответ дайте в градусах\s*\.",
    ),
    (
        "tangent_chord",
        rf"Хорда AB\s+стягивает дугу окружности в\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите угол ABC\s+между этой хордой и касательной к окружности, проведенной через точку B"
        + END,
    ),
    (
        "central_from_tangent",
        rf"Через концы A\s+и\s+B\s+дуги окружности с центром O\s+проведены касательные AC\s+и\s+BC\s*\.\s*Угол CAB\s+равен\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите угол AOB"
        + END,
    ),
    (
        "two_tangents_angle",
        rf"Через концы A\s*,\s*B\s+дуги окружности в\s+(.+?)\s*{DEGREE}\s+проведены касательные AC\s+и\s+BC\s*\.\s*Найдите угол ACB"
        + END,
    ),
    (
        "two_tangents_arc",
        rf"Касательные CA\s+и\s+CB\s+к окружности образуют угол ACB\s*,\s*равный\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите величину меньшей дуги AB\s*,\s*стягиваемой точками касания"
        + END,
    ),
    (
        "near_angle",
        PREFIX
        + rf"(?:сторона CO\s+пересекает окружность в точке B\s*,\s*дуга AB\s+окружности|а меньшая дуга окружности AB\s*)\s*,\s*заключенная внутри этого угла, равна\s+(.+?)\s*{DEGREE}"
        + END,
    ),
    (
        "near_arc",
        rf"Угол ACO\s+равен\s+(.+?)\s*{DEGREE}\s*,\s*где O\s*[—–-]\s*центр окружности\s*\.\s*Его сторона CA\s+касается окружности\s*\.\s*Найдите величину меньшей дуги AB\s+окружности, заключенной внутри этого угла"
        + END,
    ),
    (
        "far_angle",
        PREFIX
        + rf"(?:сторона CO\s+пересекает окружность в точках B\s+и\s+D\s*,\s*а дуга AD\s+окружности|а большая дуга AD\s+окружности)\s*,\s*заключенная внутри этого угла, равна\s+(.+?)\s*{DEGREE}"
        + END,
    ),
    (
        "far_arc",
        rf"Угол ACO\s+равен\s+(.+?)\s*{DEGREE}\s*\.\s*Его сторона CA\s+касается окружности с центром в точке O\s*\.\s*Сторона CO\s+пересекает окружность в точках B\s+и\s+D\s*\(см\.\s*рис\.\)\s*\.?\s*Найдите градусную меру дуги AD\s+окружности, заключенной внутри этого угла"
        + END,
    ),
)


@dataclass(frozen=True)
class TangentQuantity:
    mode: str
    given: tuple[sp.Expr, ...]
    answer: sp.Expr


def _model(mode, given):
    a, b = given[0], given[1] if len(given) == 2 else sp.S.Zero
    if mode == "chord":
        if a not in (30, 120):
            raise ContentPlanError(
                "the reviewed chord methods require 30 or 120 degrees"
            )
        return TangentQuantity(
            "chord_thirty" if a == 30 else "chord_obtuse",
            given,
            sp.simplify(2 * b * sp.sin(sp.pi * a / 180)),
        )
    valid, answer = {
        "arc_ratio": (a != b, 180 * max(a, b) / (a + b)),
        "tangent_chord": (a < 180, a / 2),
        "central_from_tangent": (a < 90, 2 * a),
        "two_tangents_angle": (a < 180, 180 - a),
        "two_tangents_arc": (a < 180, 180 - a),
        "near_angle": (a < 90, 90 - a),
        "near_arc": (a < 90, 90 - a),
        "far_angle": (90 < a < 180, a - 90),
        "far_arc": (a < 90, a + 90),
    }[mode]
    if not valid:
        raise ContentPlanError(
            "the reviewed tangent or distinct-arc configuration is impossible"
        )
    return TangentQuantity(mode, given, sp.simplify(answer))


def read_question(html, source=None):
    try:
        text = _text(
            html,
            source,
            labels="ABCDO",
            extra_identifiers=(
                "AB",
                "AC",
                "BC",
                "CA",
                "CB",
                "CO",
                "BD",
                "DB",
                "AD",
                "ABC",
                "ACB",
                "CAB",
                "AOB",
                "ACO",
            ),
        ).replace("ё", "е")
        for mode, pattern in PATTERNS:
            match = re.fullmatch(pattern, text)
            if match:
                return _model(
                    mode, tuple(_parse_positive_value(v) for v in match.groups())
                )
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError(
        "one complete reviewed chord or tangent question is required"
    )
