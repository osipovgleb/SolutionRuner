"""Reject edge-only intersections before applying the two-volume section formula."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .pyramid_model import regular
from .spatial_metric_model import model

MODES = {"triangle_perpendicular_section_area"}
HEADER = r"[ВB] правильной треугольной пирамиде SABC "
RATIO = (
    r"провели сечение плоскостью, проходящей через сторону основания AB перпендикулярно ребру SC\. "
    r"Докажите, что площадь этого сечения относится к площади основания так же, как высота пирамиды относится к ее боковому ребру\. "
    r"Найдите площадь сечения если боковое ребро SA\s*=\s*(.+?), а сторона основания AB\s*=\s*(.+?)\."
)
GIVENS = r"боковое ребро SA\s*=\s*(.+?), а сторона основания AB\s*=\s*(.+?)\. "
VOLUME = (
    r"Докажите, что утроенный объем пирамиды SABC равен произведению ребра SC на площадь сечения пирамиды плоскостью, проходящей через ребро AB перпендикулярно ребру SC\. "
    r"Найдите площадь этого сечения\."
)
PLAIN = r"Найдите площадь сечения пирамиды плоскостью, проходящей через ребро AB перпендикулярно ребру SC\."


def _solve(groups, claim):
    e, a = map(positive, groups)
    q = regular("triangle", {"a": a, "e": e})
    q["foot"] = sp.simplify(a * a / (2 * e * e))
    if q["foot"] > 1:
        raise ContentPlanError(
            "the perpendicular plane meets the pyramid only along AB; no two-dimensional section exists"
        )
    q.update(CK=sp.simplify(q["foot"] * e), SK=sp.simplify((1 - q["foot"]) * e))
    return model(
        "triangle_perpendicular_section_area",
        (("e", e), ("a", a)),
        q,
        (claim,),
        q["B"] * q["H"] / e,
    )


def read(raw):
    for suffix, claim in (
        (RATIO, "ratio"),
        (GIVENS + VOLUME, "volume"),
        (GIVENS + PLAIN, "plain"),
    ):
        match = re.fullmatch(HEADER + suffix, raw)
        if match:
            try:
                return _solve(match.groups(), claim)
            except UnsupportedCondition as exc:
                raise ContentPlanError(
                    "complete numeric section measurements are required"
                ) from exc
    return None
