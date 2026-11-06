"""Two orthogonal projections share the rectangular-box coordinates and plane normals."""

import re
from dataclasses import replace

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from . import box_coordinates as c
from .measurements import positive
from .spatial_metric_model import model

MODES = {"box_tetrahedron_line_projection_angle"}
DIMENSIONS = r"AA_1\s*=\s*(.+?), AB\s*=\s*(.+?), BC\s*=\s*(.+?)\."
PAIR = r"(A_1BC и прямой BC_1|AA_1C и прямой A_1B)"
FACES = (
    r"Дан прямоугольный параллелепипед ABCDA_1B_1C_1D_1\. "
    r"Докажите, что все грани тетраэдра ACB_1D_1 — равные треугольники "
    r"\(тетраэдр, обладающий таким свойством, называют равногранным\)\. "
    r"[ВB] прямоугольном параллелепипеде ABCDA_1B_1C_1D_1 найдите угол между плоскостью "
    + PAIR
    + r", если "
    + DIMENSIONS
)
PERPENDICULAR = (
    r"[ВB] прямоугольном параллелепипеде ABCDA_1B_1C_1D_1\s*"
    + DIMENSIONS
    + r" Докажите, что плоскости DA_1B и AA_1C перпендикулярны\. "
    r"Найдите угол между плоскостью AA_1C и прямой A_1B\."
)


def _solve(pair, values, claim):
    h, a, b = map(positive, values)
    p = c.points((a, b, h))
    if (
        claim == "perpendicular"
        and sp.simplify(c.plane_normal("DA_1B", p).dot(c.plane_normal("AA_1C", p))) != 0
    ):
        raise ContentPlanError("the claimed box planes are not perpendicular")
    face = pair == "A_1BC и прямой BC_1"
    point, start, end = ("C_1", "C", "D_1") if face else ("B", "A", "C")
    direction = p[end] - p[start]
    foot = p[start] + direction * (p[point] - p[start]).dot(direction) / direction.dot(
        direction
    )
    distance = sp.simplify((p[point] - foot).norm())
    line = "BC_1" if face else "A_1B"
    first, last = c.endpoints(line)
    hypotenuse = (p[last] - p[first]).norm()
    normal = c.plane_normal("A_1BC" if face else "AA_1C", p)
    sine = sp.simplify(
        abs((p[last] - p[first]).dot(normal)) / (hypotenuse * normal.norm())
    )
    result = model(
        "box_tetrahedron_line_projection_angle",
        (("a", a), ("b", b), ("height", h)),
        {
            "a": a,
            "b": b,
            "height": h,
            "helper": distance,
            "hypotenuse": hypotenuse,
            "sine": sine,
            "E_x": foot[0],
            "E_y": foot[1],
            "E_z": foot[2],
        },
        ("face" if face else "diagonal", claim),
        sp.asin(sine),
    )
    return replace(result, squares=(a * a, b * b, h * h))


def read(raw):
    for pattern, claim in ((FACES, "equal_faces"), (PERPENDICULAR, "perpendicular")):
        match = re.fullmatch(pattern, raw)
        if not match:
            continue
        groups = match.groups()
        pair, values = (
            (groups[0], groups[1:])
            if claim == "equal_faces"
            else ("AA_1C и прямой A_1B", groups)
        )
        try:
            return _solve(pair, values, claim)
        except UnsupportedCondition as exc:
            raise ContentPlanError(
                "three positive box edge lengths are required"
            ) from exc
    return None
