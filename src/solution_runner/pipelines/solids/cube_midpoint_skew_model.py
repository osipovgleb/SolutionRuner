"""Translate a midpoint line through a cube vertex before finding its angle."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from . import box_coordinates as c
from .measurements import positive
from .spatial_metric_model import model

MODES = {"cube_midpoint_skew_angle"}
HEADER = (
    rf"Точка E — середина ребра (CC_1|BB_1) куба {c.HEADER}"
    r"(?: со стороной равной (.+?))?"
)
SIDE = (
    HEADER
    + r"\. Докажите, что угол между прямыми BE и AD равен углу CBE\. Найдите угол между прямыми BE и AD\."
)
PERPENDICULAR = (
    HEADER + r"\. Докажите, что B_1D\\perp AC\. Найдите угол между прямыми BE и B_1D\."
)
TRANSLATED = (
    HEADER
    + r"[.,] [Тт]очка F лежит на продолжении ребра (BB_1|CC_1) за точку (B_1|C_1), причем 2\s*(B_1F|C_1F)\s*=\s*(BB_1|CC_1)\. "
    r"Докажите, что угол между прямыми (AE|BE) и (CA_1|B_1D) равен углу между прямыми (CA_1|DB_1) и (A_1F|B_1F)\. "
    r"Найдите угол между прямыми (AE|BE) и (CA_1|B_1D)\.?"
)


def _translated(groups):
    edge, raw_a, extended, upper, measure, same, *lines = groups
    origin, vertical, far = ("A", "B", "C") if edge == "BB_1" else ("B", "C", "D")
    other = "CA_1" if origin == "A" else "B_1D"
    expected = [
        origin + "E",
        other,
        far + origin + "_1",
        origin + "_1F",
        origin + "E",
        other,
    ]
    if (
        extended != edge
        or same != edge
        or upper != vertical + "_1"
        or measure != upper + "F"
        or lines != expected
    ):
        raise ContentPlanError(
            "the translated line and the specified cube edge do not match"
        )
    return _solve("space", raw_a, origin, vertical, far, False)


def _solve(kind, raw_a, origin, vertical, far, coordinates):
    a = positive(raw_a) if raw_a else sp.Symbol("a", positive=True)
    p = c.points((a, a, a))
    E = (p[vertical] + p[vertical + "_1"]) / 2
    F = p[vertical + "_1"] + (p[vertical + "_1"] - p[vertical]) / 2
    u = E - p[origin]
    v = p[far] - p[origin + "_1"] if kind == "space" else p["D"] - p["A"]
    cosine = sp.simplify(abs(u.dot(v)) / (u.norm() * v.norm()))
    q = {
        "a": a,
        "half": a / 2,
        "cosine": cosine,
        "tangent": sp.Rational(1, 2),
        "space_diagonal": (p[far] - p[origin + "_1"]).norm(),
        "translated": (F - p[origin + "_1"]).norm(),
        "opposite": (F - p[far]).norm(),
    }
    return model(
        "cube_midpoint_skew_angle",
        (("a", a),) if raw_a else (),
        q,
        (kind, origin, vertical, far, "coordinates" if coordinates else "parallel"),
        sp.acos(cosine) if kind == "space" else sp.atan(q["tangent"]),
    )


def read(raw):
    for pattern, kind in (
        (SIDE, "side"),
        (PERPENDICULAR, "perpendicular"),
        (TRANSLATED, "translated"),
    ):
        match = re.fullmatch(pattern, raw)
        if not match:
            continue
        try:
            if kind == "translated":
                return _translated(match.groups())
            edge, raw_a = match.groups()
            if edge != "CC_1":
                raise ContentPlanError(
                    "the stated cube claim requires the midpoint of CC1"
                )
            return _solve(
                "side" if kind == "side" else "space",
                raw_a,
                "B",
                "C",
                "D",
                kind == "perpendicular",
            )
        except UnsupportedCondition as exc:
            raise ContentPlanError("a positive cube edge is required") from exc
    return None
