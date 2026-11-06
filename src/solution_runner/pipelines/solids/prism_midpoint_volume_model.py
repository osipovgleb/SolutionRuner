"""A midpoint cut divides a regular triangular prism into equal pentahedra."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {"triangle_prism_midpoint_pentahedron_volume"}
QUESTION = (
    r"[ВB] правильной треугольной призме ABCA_1B_1C_1 боковое ребро равно (.+?), а ребро основания равно (.+?)\. "
    r"Точка D — середина ребра BB_1\. Докажите, что "
    r"(расстояние между прямыми A_1D и CC_1 равно расстоянию между точкой A и плоскостью BCC_1|объемы пятигранников A_1B_1C_1CD и ABCDA_1 равны)\. "
    r"Найдите объем пятигранника (ABCA_1D|ABCDA_1|A_1B_1C_1CD)\."
)


def read(raw):
    match = re.fullmatch(QUESTION, raw)
    if not match:
        return None
    try:
        h, a = map(positive, match.groups()[:2])
    except UnsupportedCondition as exc:
        raise ContentPlanError(
            "positive triangular-prism dimensions are required"
        ) from exc
    altitude = sp.sqrt(3) * a / 2
    trapezoid = 3 * a * h / 4
    return model(
        "triangle_prism_midpoint_pentahedron_volume",
        (("H", h), ("a", a)),
        {
            "H": h,
            "a": a,
            "half_height": h / 2,
            "base_altitude": altitude,
            "trapezoid_area": trapezoid,
            "base_area": sp.sqrt(3) * a * a / 4,
            "prism_volume": sp.sqrt(3) * a * a * h / 4,
        },
        (
            "upper" if match[4] == "A_1B_1C_1CD" else "lower",
            "distance" if match[3].startswith("расстояние") else "equal_volumes",
        ),
        trapezoid * altitude / 3,
    )
