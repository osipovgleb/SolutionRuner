"""Opposite-vertex parallelograms and diagonal-normal bisector planes."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {"box_opposite_section_area", "box_diagonal_bisector_ratio"}
START = r"[ВB] прямоугольном параллелепипеде ABCDA_1B_1C_1D_1,? известны ребра:? AB\s*=\s*(.+?), AD\s*=\s*(.+?), AA_1\s*=\s*(.+?)\. "
OPPOSITE = (
    r"Точка ([WO]) принадлежит ребру (DD_1|BB_1) и делит его в отношении (.+?)(?:\\colon|:)\s*(.+?), считая от вершины ([DB])\.? "
    r"Докажите, что сечение этого параллелепипеда плоскостью, проходящей через точки (C, W и A_1|A, O и C_1)(?:, является ромбом| [—–-] параллелограмм)\. "
    r"Найдите площадь (?:этого сечения|сечения этого параллелепипеда плоскостью, проходящей через точки A, O и C_1)\."
)
NORMAL = (
    r"[ВB] прямоугольном параллелепипеде ABCDA_1B_1C_1D_1 через середину M диагонали AC_1 проведена плоскость α перпендикулярно этой диагонали, "
    r"AB\s*=\s*(.+?), BC\s*=\s*(.+?) и AA_1\s*=\s*(.+?)\. Докажите, что плоскость α содержит точку D_1\. "
    r"Найдите отношение, в котором плоскость α делит ребро A_1B_1\."
)


def _opposite(groups, rhombus):
    a, b, h = map(positive, groups[:3])
    point, edge, p, q, origin, through = groups[3:]
    if (point, edge, origin, through) not in {
        ("W", "DD_1", "D", "C, W и A_1"),
        ("O", "BB_1", "B", "A, O и C_1"),
    }:
        raise ContentPlanError("the opposite section point and ratio origin changed")
    p, q = positive(p), positive(q)
    low = h * p / (p + q)
    high = h - low
    side1 = sp.sqrt(a * a + low * low)
    side2 = sp.sqrt(b * b + high * high)
    equal = sp.simplify(side1 * side1 - side2 * side2) == 0
    if rhombus and not equal:
        raise ContentPlanError("the given dimensions do not prove the claimed rhombus")
    diagonal = sp.sqrt(a * a + b * b + h * h)
    other = sp.sqrt(a * a + b * b + (h - 2 * low) ** 2)
    dot = side1 * side1 - side2 * side2
    area = sp.sqrt(diagonal**2 * other**2 - dot**2) / 2
    return model(
        "box_opposite_section_area",
        tuple(zip(("a", "b", "height", "p", "q"), (a, b, h, p, q), strict=True)),
        {
            "a": a,
            "b": b,
            "height": h,
            "low": low,
            "high": high,
            "side1": side1,
            "side2": side2,
            "diagonal": diagonal,
            "other": other,
            "dot": dot,
            "rhombus": sp.Integer(equal),
        },
        (point, "rhombus" if rhombus else "parallelogram"),
        area,
    )


def _normal(groups):
    a, b, h = map(positive, groups)
    if sp.simplify(a * a - b * b - h * h) != 0:
        raise ContentPlanError(
            "D1 belongs to the bisector plane only when AB squared equals BC squared plus height squared"
        )
    d = sp.sqrt(a * a + b * b)
    return model(
        "box_diagonal_bisector_ratio",
        (("a", a), ("b", b), ("height", h)),
        {
            "a": a,
            "b": b,
            "height": h,
            "t": b * b / (a * a),
            "A1T": b * b / a,
            "B1T": h * h / a,
            "top_diagonal": d,
            "space_diagonal": sp.sqrt(a * a + b * b + h * h),
            "A1K": b * b / d,
            "C1K": a * a / d,
            "TK": b**3 / (a * d),
            "KD1": a * b / d,
            "TD1": b * d / a,
        },
        (),
        b * b / (h * h),
    )


def read(raw):
    raw = raw.replace(r"\alpha", "α")
    for pattern, normal in ((START + OPPOSITE, False), (NORMAL, True)):
        match = re.fullmatch(pattern, raw)
        if match:
            try:
                return (
                    _normal(match.groups())
                    if normal
                    else _opposite(match.groups(), "является ромбом" in raw)
                )
            except UnsupportedCondition as exc:
                raise ContentPlanError(
                    "complete numeric box measurements are required"
                ) from exc
    return None
