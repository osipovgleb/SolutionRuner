"""A midpoint of a lateral edge projects to a third of a base median."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .pyramid_model import regular
from .spatial_metric_model import model

MODES = {"triangle_pyramid_midpoint_projection_angle"}
QUESTION = (
    r"[ВB] правильной треугольной пирамиде SABC с основанием ABC известны ребра:? AB\s*=\s*(.+?),+ SC\s*=\s*(.+?)\. "
    r"(M — середина ребра (?:SA|AS)\. )?Докажите, что "
    r"(проекции точек S и M на плоскость основания делят высоту AN треугольника ABC на три равные части|AS\\perp BC)\. "
    r"Найдите угол, образованный плоскостью основания и (прямой MN|прямой, проходящей через середины ребер AS и BC)\."
)


def read(raw):
    match = re.fullmatch(QUESTION, raw)
    if not match:
        return None
    a, e, midpoint, claim, request = match.groups()
    trisection = claim.startswith("проекции")
    if trisection and not midpoint or request == "прямой MN" and not trisection:
        raise ContentPlanError(
            "the stated projections require the named midpoint and base median"
        )
    try:
        a, e = positive(a), positive(e)
    except UnsupportedCondition as exc:
        raise ContentPlanError(
            "positive base and lateral pyramid edges are required"
        ) from exc
    q = regular("triangle", {"a": a, "e": e})
    q.update(
        AN=sp.sqrt(3) * a / 2,
        AM=e / 2,
        AM1=sp.sqrt(3) * a / 6,
        M1N=sp.sqrt(3) * a / 3,
        AO=sp.sqrt(3) * a / 3,
        MM1=q["H"] / 2,
    )
    q["tan"] = sp.simplify(q["MM1"] / q["M1N"])
    return model(
        "triangle_pyramid_midpoint_projection_angle",
        (("a", a), ("e", e)),
        q,
        ("trisection" if trisection else "perpendicular",),
        sp.atan(q["tan"]),
    )
