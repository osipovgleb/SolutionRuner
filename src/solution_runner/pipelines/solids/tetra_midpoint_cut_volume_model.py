"""A parallel trapezoid section splits an arbitrary tetrahedron into two volumes."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {"tetra_midpoint_cut_volume_ratio"}
COLON = r"\s*(?::|\\colon)\s*"
QUESTION = (
    r"На ребрах AB и BC треугольной пирамиды ABCD отмечены точки M и N соответственно, причем "
    + r"AM"
    + COLON
    + r"(?:BM|MB)\s*=\s*CN"
    + COLON
    + r"NB\s*=\s*(.+?)"
    + COLON
    + r"(.+?)\. Точки P и Q — середины (?:ребер|сторон) DA и DC соответственно\. "
    r"(?:Докажите|Доказать), что P, Q, M и N лежат в одной плоскости\. "
    r"Найти отношение объемов многогранников, на которые плоскость PQM разбивает пирамиду\."
)


def read(raw):
    match = re.fullmatch(QUESTION, raw)
    if not match:
        return None
    try:
        u, v = map(positive, match.groups())
    except UnsupportedCondition as exc:
        raise ContentPlanError("two positive edge-division terms are required") from exc
    t = sp.simplify(u / (u + v))
    fraction = sp.simplify(t * (5 - 2 * t) / 4)
    return model(
        "tetra_midpoint_cut_volume_ratio",
        (("u", u), ("v", v)),
        {
            "fraction": t,
            "small_base_fraction": (1 - t) ** 2,
            "trapezoid_fraction": 1 - (1 - t) ** 2,
            "QCN_fraction": t / 2,
            "PQCN_volume": t / 4,
            "PACNM_volume": (1 - (1 - t) ** 2) / 2,
            "left_volume": fraction,
            "right_volume": 1 - fraction,
        },
        (),
        fraction / (1 - fraction),
    )
