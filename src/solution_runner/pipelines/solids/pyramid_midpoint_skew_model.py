"""A base median and a lateral-edge midpoint determine one skew-line cosine."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..equations.power_arithmetic import ScalarParser
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .pyramid_model import regular
from .spatial_metric_model import model

MODES = {"triangle_pyramid_midpoint_skew_cosine"}
QUESTION = (
    r"Боковое ребро правильной треугольной пирамиды SABC равно (.+?), а косинус угла ASB при вершине боковой грани равен (.+?)\. "
    r"Точка M — середина ребра SC(?:, точка N — середина ребра AC)?\. Докажите, что "
    r"(угол между прямыми BM и SA либо равен углу BMN, либо дополняет его до 180°|BC\\perp SA|BS\\perp AC)\. "
    r"Найдите косинус угла между прямыми BM и SA\."
)


def read(raw):
    match = re.fullmatch(QUESTION, raw)
    if not match:
        return None
    try:
        e, c = positive(match[1]), ScalarParser(match[2]).parse()
    except UnsupportedCondition as exc:
        raise ContentPlanError(
            "an exact lateral edge and face-angle cosine are required"
        ) from exc
    if (
        c.is_real is not True
        or c.is_finite is not True
        or not (-sp.Rational(1, 2) < c < 1)
    ):
        raise ContentPlanError(
            "the face cosine must define a nondegenerate regular pyramid"
        )
    claim = match[3]
    if claim.startswith("угол") and ", точка N — середина ребра AC" not in raw:
        raise ContentPlanError(
            "the claimed angle requires the specified base midpoint N"
        )
    a = e * sp.sqrt(2 * (1 - c))
    q = regular("triangle", {"a": a, "e": e})
    q.update(
        face_cosine=c,
        MN=e / 2,
        BM=e * sp.sqrt(5 - 4 * c) / 2,
        BN=a * sp.sqrt(3) / 2,
        signed_cosine=c / sp.sqrt(5 - 4 * c),
        cosine=abs(c) / sp.sqrt(5 - 4 * c),
    )
    return model(
        "triangle_pyramid_midpoint_skew_cosine",
        (("e", e), ("c", c)),
        q,
        (
            "angle"
            if claim.startswith("угол")
            else "SA_BC"
            if claim.startswith("BC")
            else "SB_AC",
        ),
        q["cosine"],
    )
