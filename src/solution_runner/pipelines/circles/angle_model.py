"""Read complete circle-angle questions and derive exact angles from arc relations."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from ..quadrilaterals.trapezoid.isosceles_model import DEGREE
from ..triangles.right.altitude_input import _text
from ..triangles.right.altitude_solver import AltitudeSolveError, _parse_positive_value

RULES = {
    "circle-central-angle-difference": "central_difference",
    "circle-inscribed-angle-difference": "difference_equation",
    "circle-inscribed-angle-arc-fraction": "fraction",
    "circle-inscribed-angle-two-arcs": "two_arcs",
    "circle-diameters-inscribed-to-central": "diameters_central",
    "circle-diameters-central-to-inscribed": "diameters_inscribed",
    "circle-secant-angle-arc-difference": "secants",
}
END = r"\s*\.\s*Ответ дайте в градусах\s*\."
DIAMETERS = r"(?:[ВB] окружности с центром O\s+(?:отрезки\s+)?AC\s+и\s+BD\s*[—–-]\s*диаметры|Отрезки AC\s+и\s+BD\s*[—–-]\s*диаметры окружности с центром O\s*)\s*\.\s*"
PATTERNS = (
    (
        "central_difference",
        rf"Найдите центральный угол AOB\s*,\s*если он на\s+(.+?)\s*{DEGREE}\s+больше вписанного угла ACB\s*,\s*опирающегося на ту же дугу"
        + END,
    ),
    (
        "difference_equation",
        rf"Центральный угол(?: окружности)? на\s+(.+?)\s*{DEGREE}\s+больше (?:острого )?вписанного угла, опирающегося на ту же дугу (?:данной )?окружности\s*\.\s*Найдите (вписанный|центральный) угол"
        + END,
    ),
    (
        "fraction",
        r"Найдите вписанный угол, опирающийся на дугу, которая составляет\s+(.+?)\s+окружности"
        + END,
    ),
    (
        "fraction",
        r"Найдите вписанный угол ABC\s*,\s*опирающийся на дугу AC\s*,\s*длина которой равна\s+(.+?)\s+длины окружности"
        + END,
    ),
    (
        "two_arcs",
        rf"Дуга окружности AC\s*,\s*не содержащая точки B\s*,\s*составляет\s+(.+?)\s*{DEGREE}\s*\.\s*[АA] дуга окружности BC\s*,\s*не содержащая точки A\s*,\s*составляет\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите вписанный угол ACB"
        + END,
    ),
    (
        "diameters_central",
        DIAMETERS
        + rf"(?:Вписанный угол|Угол) ACB\s+равен\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите (?:центральный угол|величину угла) AOD"
        + END,
    ),
    (
        "diameters_inscribed",
        DIAMETERS
        + rf"(?:Центральный угол|Угол) AOD\s+равен\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите вписанный угол ACB"
        + END,
    ),
    (
        "secants",
        rf"Угол ACB\s+равен\s+(.+?)\s*{DEGREE}\s*\.\s*Градусная (?:величина|мера) дуги AB\s+окружности, не содержащей точек D\s+и\s+E\s*,\s*равна\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите угол DAE"
        + END,
    ),
)


@dataclass(frozen=True)
class CircleAngle:
    mode: str
    given: tuple[sp.Expr, ...]
    answer: sp.Expr
    central: bool = False
    named: bool = False
    percent: bool = False


def _model(mode, groups, text):
    central = mode == "central_difference" or (
        mode == "difference_equation" and groups[-1] == "центральный"
    )
    values = groups[:1] if mode == "difference_equation" else groups
    percent = mode == "fraction" and values[0].endswith("%")
    given = tuple(
        _parse_positive_value(v.removesuffix("%").strip() if percent else v)
        for v in values
    )
    a, b = given[0], given[1] if len(given) == 2 else sp.S.Zero
    fraction = a / 100 if percent else a
    near = b - 2 * a
    difference_valid = a <= 90 and not ("острого" in text and a == 90)
    difference = (
        difference_valid,
        2 * a if central else a,
        "the named central or acute inscribed angle is impossible",
    )
    valid, answer, reason = {
        "central_difference": difference,
        "difference_equation": difference,
        "fraction": (
            fraction < 1,
            180 * fraction,
            "the intercepted arc must be less than a full circle",
        ),
        "two_arcs": (
            a + b < 360,
            (360 - a - b) / 2,
            "the two disjoint arcs must leave a positive third arc",
        ),
        "diameters_central": (
            a < 90,
            180 - 2 * a,
            "the given inscribed angle between diameters must be acute",
        ),
        "diameters_inscribed": (
            a < 180,
            (180 - a) / 2,
            "the given central angle must be nondegenerate",
        ),
        "secants": (
            near > 0 and b + near < 360,
            near / 2,
            "the secant arcs must be positive and disjoint",
        ),
    }[mode]
    if not valid:
        raise ContentPlanError(reason)
    return CircleAngle(
        mode, given, sp.simplify(answer), central, "ABC" in text, percent
    )


def read_question(html, source=None):
    try:
        text = _text(
            html,
            source,
            labels="ABCDEO",
            extra_identifiers=(
                "AOB",
                "ACB",
                "AOD",
                "ABC",
                "DAE",
                "AC",
                "BC",
                "AB",
                "BD",
            ),
        ).replace("ё", "е")
        for mode, pattern in PATTERNS:
            match = re.fullmatch(pattern, text)
            if match:
                return _model(mode, match.groups(), text)
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError("one complete reviewed circle-angle question is required")
