"""A regular tetrahedron cut through equal edge points: volumes and plane cosine."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .pyramid_model import regular
from .spatial_metric_model import model

MODES = {"tetra_equal_edge_cut_cosine"}
QUESTION = (
    r"[ВB] правильном тетраэдре ABCD все ребра равны (.+?)\. На ребрах AB и AD отмечены точки M и K соответственно так, что AM\s*=\s*AK\s*=\s*(.+?)\. "
    r"Докажите, что плоскость CMK делит тетраэдр ABCD на два многогранника, объемы которых относятся как (.+?):\s*(.+?)\. "
    r"Найдите косинус угла между плоскостью CBD и плоскостью CMK\."
)


def read(raw):
    match = re.fullmatch(QUESTION, raw.replace(r"\colon", ":"))
    if not match:
        return None
    try:
        a, t, p, q = map(positive, match.groups())
    except UnsupportedCondition as exc:
        raise ContentPlanError(
            "complete positive tetrahedron measurements are required"
        ) from exc
    if not 0 < t < a:
        raise ContentPlanError("the cut points must lie strictly inside the two edges")
    ratio = sp.simplify((a * a - t * t) / (t * t))
    if sp.simplify(ratio - p / q) == 0:
        order = "remaining"
    elif sp.simplify(1 / ratio - p / q) == 0:
        order = "corner"
    else:
        raise ContentPlanError("the claimed volumes do not follow from the edge points")
    dims = regular("triangle", {"a": a, "e": a})
    side = sp.sqrt(a * a - a * t + 3 * t * t / 4)
    cosine = sp.simplify((2 * a + t) / (2 * sp.sqrt(3) * side))
    dims.update(
        t=t,
        p=p,
        q=q,
        ratio=ratio,
        AA1=t * sp.sqrt(3) / 2,
        AA2=a * sp.sqrt(3) / 2,
        A1A2=(a - t) * sp.sqrt(3) / 2,
        CA1=side,
        CA2=a * sp.sqrt(3) / 2,
        cosine=cosine,
        total_coefficient=a * a * sp.sqrt(3) / 12,
        corner_coefficient=t * t * sp.sqrt(3) / 12,
        remaining_coefficient=(a * a - t * t) * sp.sqrt(3) / 12,
        center_side=2 * a - 3 * t,
    )
    return model(
        "tetra_equal_edge_cut_cosine",
        (("a", a), ("t", t), ("p", p), ("q", q)),
        dims,
        (order,),
        cosine,
    )
