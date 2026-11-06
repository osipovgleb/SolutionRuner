"""The plane through two lateral-edge midpoints of a regular square pyramid."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .pyramid_model import regular
from .spatial_metric_model import model

MODES = {"square_pyramid_midpoint_plane_angle"}
QUESTION = (
    r"[ВB] правильной четырехугольной пирамиде SABCD(?: с основанием ABCD| точка S — вершина\.)? "
    r"[Тт]очка M — середина ребра SA, точка K — середина ребра SC\. "
    r"(?:а\) )?Докажите, что прямые SB и MK перпендикулярны\. "
    r"(?:б\)\s*)?Найдите угол между плоскостями BMK и ABC, если AB\s*=\s*(.+?), SC\s*=\s*(.+?)\."
)


def read(raw):
    match = re.fullmatch(QUESTION, raw)
    if not match:
        return None
    try:
        a, edge = map(positive, match.groups())
    except UnsupportedCondition as exc:
        raise ContentPlanError(
            "complete positive pyramid measurements are required"
        ) from exc
    q = regular("square", {"a": a, "e": edge})
    q.update(BO=q["R"], QO=q["H"] / 2)
    q["tan"] = q["QO"] / q["BO"]
    return model(
        "square_pyramid_midpoint_plane_angle",
        (("a", a), ("edge", edge)),
        q,
        (),
        sp.atan(q["tan"]),
    )
