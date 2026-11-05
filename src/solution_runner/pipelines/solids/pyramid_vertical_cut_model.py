"""Validate when a vertical edge-point plane contains the opposite base vertex."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .pyramid_model import regular
from .spatial_metric_model import model

MODES = {"square_vertical_vertex_area"}
HEADER = (
    r"[ВB] правильной четырехугольной пирамиде SABCD сторона основания AB равна (.+?), а боковое ребро SA равно (.+?)\. "
    r"На ребрах AB и SB отмечены точки M и K соответственно, причем "
)
POINTS = (r"AM\s*=\s*(.+?), SK\s*=\s*(.+?)\. ", r"AM\s*=\s*SK\s*=\s*(.+?)\. ")
REQUEST = (
    r"Плоскость α перпендикулярна плоскости ABC и содержит точки M и K\. "
    r"Докажите, что плоскость α содержит точку C\. "
    r"Найдите площадь сечения пирамиды SABCD плоскостью α\."
)


def _solve(groups):
    a, e, am = map(positive, groups[:3])
    sk = positive(groups[3]) if len(groups) == 4 else am
    if not (am < a and sk < e):
        raise ContentPlanError("M and K must be interior points of AB and SB")
    b, r = a - am, (e - sk) / e
    if sp.simplify(r - 2 * b / (a + b)) != 0:
        raise ContentPlanError("the given vertical plane does not contain C")
    q = regular("square", {"a": a, "e": e})
    q.update(
        AM=am,
        SK=sk,
        BM=b,
        BK=e - sk,
        fraction=r,
        section_base=sp.sqrt(a * a + b * b),
        section_height=r * q["H"],
    )
    return model(
        "square_vertical_vertex_area",
        (("a", a), ("e", e), ("AM", am), ("SK", sk)),
        q,
        (),
        q["section_base"] * q["section_height"] / 2,
    )


def read(raw):
    raw = raw.replace(r"\alpha", "α")
    for points in POINTS:
        match = re.fullmatch(HEADER + points + REQUEST, raw)
        if match:
            try:
                return _solve(match.groups())
            except UnsupportedCondition as exc:
                raise ContentPlanError(
                    "complete numeric section measurements are required"
                ) from exc
    return None
