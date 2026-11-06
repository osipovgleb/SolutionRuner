"""Translate hexagonal-base directions into an isosceles lateral triangle."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .pyramid_model import regular
from .spatial_metric_model import hex_points, model

MODES = {"hexagonal_pyramid_skew_angle"}
ANGLE = (
    r"Дана правильная шестиугольная пирамида SABCDEF\. "
    r"Докажите, что угол между прямыми SB и CD равен углу SBE\. "
    r"Если стороны основания равны (.+?), а боковые ребра равны (.+?), найдите угол между прямыми SB и CD\."
)
COSINE = (
    r"(?:[ВB] правильной шестиугольной пирамиде SABCDEF стороны основания|Дана правильная шестиугольная пирамида SABCDEF стороны основания которой) "
    r"равны (.+?), а боковые ребра равны (.+?)\. "
    r"Докажите, что плоскость (SBD|SBC) параллельна прямой (AE|AD)\. "
    r"[Нн]айдите косинус угла между прямыми SB и AD\."
)


def read(raw):
    match = re.fullmatch(ANGLE, raw)
    cosine = False
    if not match:
        match = re.fullmatch(COSINE, raw)
        cosine = True
    if not match:
        return None
    try:
        a, e = map(positive, match.groups()[:2])
        q = regular("hexagon", {"a": a, "e": e})
    except UnsupportedCondition as exc:
        raise ContentPlanError(
            "positive nondegenerate hexagonal-pyramid edges are required"
        ) from exc
    points = hex_points(a, q["H"])
    claim = "angle_equal"
    if cosine:
        plane, line = match.groups()[2:]
        if (plane, line) not in {("SBD", "AE"), ("SBC", "AD")}:
            raise ContentPlanError(
                "the stated base line is not parallel to the specified plane"
            )
        claim = plane
    direction = points["D"] - points["A" if cosine else "C"]
    lateral = points["B"] - points["S"]
    q["cosine"] = sp.simplify(
        abs(lateral.dot(direction)) / (lateral.norm() * direction.norm())
    )
    q["chord"] = a if cosine else 2 * a
    q["half_chord"] = q["chord"] / 2
    return model(
        "hexagonal_pyramid_skew_angle",
        (("a", a), ("e", e)),
        q,
        ("AD" if cosine else "CD", "cosine" if cosine else "angle", claim),
        q["cosine"] if cosine else sp.acos(q["cosine"]),
    )
