"""One diametral projection gives the angle, altitude or lateral cylinder area."""

import re
from dataclasses import replace

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {"cylinder_axis_chord_geometry"}
QUESTIONS = {
    "угол между прямыми BB_1 и AC_1": "angle",
    "расстояние от точки B до прямой AC_1": "distance",
    "площадь боковой поверхности цилиндра": "lateral_area",
}
HEADER = (
    r"[ВB] цилиндре образующая перпендикулярна плоскости основания\. "
    r"На окружности одного из оснований цилиндра выбраны точки A и B, а на окружности другого основания — точки B_1 и C_1, "
    r"причем BB_1 — образующая цилиндра, а отрезок AC_1 пересекает ось цилиндра\. "
    r"Докажите, что угол ABC_1 прямой\. Найдите "
)
MEASUREMENTS = r", если AB\s*=\s*(.+?), BB_1\s*=\s*(.+?), B_1C_1\s*=\s*(.+?)\."


def read(raw):
    for question, target in QUESTIONS.items():
        match = re.fullmatch(HEADER + re.escape(question) + MEASUREMENTS, raw)
        if not match:
            continue
        try:
            a, h, b = map(positive, match.groups())
        except UnsupportedCondition as exc:
            raise ContentPlanError(
                "three positive cylinder chords and height are required"
            ) from exc
        diameter = sp.sqrt(a * a + b * b)
        side = sp.sqrt(b * b + h * h)
        diagonal = sp.sqrt(a * a + b * b + h * h)
        q = {
            "AB": a,
            "H": h,
            "B1C1": b,
            "diameter": diameter,
            "radius": diameter / 2,
            "BC1": side,
            "AC1": diagonal,
            "tangent": diameter / h,
            "distance": a * side / diagonal,
            "lateral_area": sp.pi * diameter * h,
        }
        answer = sp.atan(q["tangent"]) if target == "angle" else q[target]
        return replace(
            model(
                "cylinder_axis_chord_geometry",
                (("a", a), ("H", h), ("b", b)),
                q,
                (target,),
                answer,
            ),
            symbols={"coordinate_method": "no" if target == "lateral_area" else "yes"},
        )
    return None
