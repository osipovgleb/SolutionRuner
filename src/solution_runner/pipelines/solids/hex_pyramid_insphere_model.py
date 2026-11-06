"""A regular hexagonal pyramid shares one inradius across all its tangent faces."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .pyramid_model import regular
from .spatial_metric_model import model

MODES = {"hexagonal_pyramid_insphere_area"}
COLON = r"\s*(?::|\\colon)\s*"
QUESTION = (
    r"[ВB] правильную шестиугольную пирамиду, боковое ребро которой равно (.+?), а высота равна (.+?), вписана сфера\. "
    r"\(Сфера касается всех граней пирамиды\.\) Докажите, что (.+?)\. Найдите площадь этой сферы\."
)
SURFACE = (
    r"площадь боковой поверхности пирамиды относится к площади основания как (.+?)"
    + COLON
    + r"(.+?)"
)
ANGLE = r"двугранный угол при основании пирамиды равен (.+?)°"


def _claim(raw, q):
    match = re.fullmatch(SURFACE, raw)
    if match:
        left, right = map(positive, match.groups())
        if sp.simplify(q["L"] / q["B"] - left / right) != 0:
            raise ContentPlanError(
                "the pyramid dimensions do not give the claimed surface ratio"
            )
        q.update(claimed_left=left, claimed_right=right)
        return "surface_ratio"
    match = re.fullmatch(ANGLE, raw)
    if match:
        degrees = positive(match[1])
        if (
            not 0 < degrees < 90
            or sp.simplify(q["H"] / q["l"] - sp.sin(degrees * sp.pi / 180)) != 0
        ):
            raise ContentPlanError(
                "the pyramid dimensions do not give the claimed dihedral angle"
            )
        q["claimed_degrees"] = degrees
        return "dihedral_angle"
    raise ContentPlanError(
        "the inscribed-sphere proof requires a reviewed pyramid claim"
    )


def read(raw):
    match = re.fullmatch(QUESTION, raw)
    if not match:
        return None
    try:
        e, h = map(positive, match.groups()[:2])
        q = regular("hexagon", {"e": e, "H": h})
        claim = _claim(match[3], q)
    except UnsupportedCondition as exc:
        raise ContentPlanError(
            "positive exact pyramid dimensions and a complete claim are required"
        ) from exc
    radius = sp.simplify(h * q["r"] / (q["l"] + q["r"]))
    q.update(
        sphere_radius=radius, sphere_area=sp.factor(sp.expand(4 * sp.pi * radius**2))
    )
    return model(
        "hexagonal_pyramid_insphere_area",
        (("e", e), ("H", h)),
        q,
        (claim,),
        q["sphere_area"],
    )
