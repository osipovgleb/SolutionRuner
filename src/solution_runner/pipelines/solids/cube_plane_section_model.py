"""Validate the midpoint plane before calculating the parent's volume method."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from .measurements import positive
from .pyramid_model import root
from .spatial_metric_model import model

MODES = {"cube_base_plane_distance", "cube_vertical_plane_distance"}
QUESTION = (
    r"На ребрах (CD|DD_1) и BB_1 куба ABCDA_1B_1C_1D_1 с ребром (.+?) отмечены точки P и Q соответственно, причем DP\s*=\s*(.+?), а B_1Q\s*=\s*(.+?)\. "
    r"Плоскость (A_1|A)PQ пересекает ребро CC_1 в точке M\. Докажите, что точка M является серединой ребра CC_1\. "
    r"Найдите расстояние от точки (C_1|C) до плоскости (A_1|A)PQ\."
)


def _solve(groups):
    edge, raw_a, raw_p, raw_b, apex, target, plane = groups
    a, p, b = map(positive, (raw_a, raw_p, raw_b))
    vertical = edge == "DD_1"
    if (apex, target, plane) != (
        ("A_1", "C_1", "A_1") if vertical else ("A", "C", "A")
    ) or not (p < a and b < a):
        raise ContentPlanError(
            "the cube edges, plane and requested vertex need one reviewed construction"
        )
    cm = p - b if vertical else (a - b) * (a - p) / a
    if sp.simplify(cm - a / 2) != 0:
        raise ContentPlanError("the given section does not bisect CC1")
    q = {"a": a, "p": p, "b": b, "H": a, "CM": cm, "C1M": a - cm, "BQ": a - b}
    if vertical:
        q.update(
            PM=root(a * a + b * b),
            MQ=root(a * a + (a - p) ** 2),
            PQ=root(2 * a * a + (p + b - a) ** 2),
        )
        first, second, third = q["PM"], q["MQ"], q["PQ"]
        q.update(
            V=a * a * (a - cm) / 6,
            nx=-b / (a - p),
            ny=sp.Integer(1),
            nz=a / (a - p),
            constant=-a * (a - b) / (a - p),
        )
    else:
        rc = a * (a - p) / p
        q.update(
            RC=rc,
            RB=rc + a,
            PC=a - p,
            RP=root(rc * rc + (a - p) ** 2),
            RM=root(rc * rc + cm * cm),
            MP=root((a - p) ** 2 + cm * cm),
        )
        first, second, third = q["RM"], q["RP"], q["MP"]
        q.update(
            V=rc * (a - p) * cm / 6,
            nx=a / p,
            ny=sp.Integer(1),
            nz=a * a / (p * (a - b)),
            constant=-a * a / p,
        )
    cosine = sp.simplify(
        (first * first + second * second - third * third) / (2 * first * second)
    )
    sine = root(1 - cosine * cosine)
    q.update(cosine=cosine, sine=sine, face_area=first * second * sine / 2)
    return model(
        "cube_vertical_plane_distance" if vertical else "cube_base_plane_distance",
        (("a", a), ("p", p), ("b", b)),
        q,
        (),
        3 * q["V"] / q["face_area"],
    )


def read(raw):
    match = re.fullmatch(QUESTION, raw)
    return _solve(match.groups()) if match else None
