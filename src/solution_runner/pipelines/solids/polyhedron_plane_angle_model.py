"""Cube projection proofs and parallel diagonal planes of a rectangular box."""

import re
from dataclasses import replace

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from . import box_coordinates as c
from .measurements import positive
from .spatial_metric_model import model

MODES = {"cube_projection_plane_angle", "box_parallel_plane_angle"}
PLANE = rf"(?:{c.VERTEX}){{3}}"
CUBE = rf"(?:[ВB] кубе {c.HEADER} |Дан куб {c.HEADER}\. )"
CUBE_CLAIMS = (
    (
        rf"Докажите, что плоскость ({PLANE}) и прямая ({c.SEGMENT}) перпендикулярны\. ",
        False,
    ),
    (
        rf"Докажите, что плоскость ({PLANE}) перпендикулярна прямой ({c.SEGMENT})\. ",
        False,
    ),
    (rf"Докажите, что плоскости ({PLANE}) и ({PLANE}) перпендикулярны\. ", True),
)
CUBE_QUANTITY = (
    rf"Найдите (косинус угла|угол) между плоскостями ({PLANE}) и ({PLANE})\."
)
BOX = (
    r"Дан параллелепипед ABCDA_1B_1C_1D_1\. Докажите, что плоскости A_1BD и B_1CD_1 параллельны\. "
    r"Пусть (?:дополнительно известно, что|известно еще, что) параллелепипед прямоугольный, (?:а )?кроме того AB\s*=\s*(.+?), BC\s*=\s*(.+?), CC_1\s*=\s*(.+?)\. "
    r"Найдите (тангенс угла|угол) между плоскостями (CDD_1 и BDA_1|ACD_1 и A_1B_1C_1|ABC и A_1DB)\."
)


def _vertices(plane):
    return frozenset(re.findall(c.VERTEX, plane))


def _cube(groups, planes):
    first, second, quantity, p1, p2 = groups
    vertices = c.points((sp.S.One,) * 3)
    if planes:
        n, m = c.plane_normal(first, vertices), c.plane_normal(second, vertices)
        if sp.simplify(n.dot(m)) != 0:
            raise ContentPlanError("the claimed cube planes are not perpendicular")
        if {_vertices(first), _vertices(second)} != {
            _vertices("AB_1D_1"),
            _vertices("A_1BC"),
        }:
            raise ContentPlanError(
                "this cube perpendicular-plane construction needs review"
            )
        claim = "planes"
    else:
        a, b = c.endpoints(second)
        n = c.plane_normal(first, vertices)
        if sp.simplify(n.cross(vertices[b] - vertices[a]).norm()) != 0:
            raise ContentPlanError(
                "the claimed cube line is not perpendicular to the plane"
            )
        if (_vertices(first), frozenset((a, b))) == (
            _vertices("BA_1C_1"),
            frozenset(("B_1", "D")),
        ):
            claim = "B1D"
        elif (_vertices(first), frozenset((a, b))) == (
            _vertices("B_1CD_1"),
            frozenset(("A", "C_1")),
        ):
            claim = "AC1"
        else:
            raise ContentPlanError("this cube projection proof needs review")
    pair = {_vertices(p1), _vertices(p2)}
    if pair == {_vertices("BA_1C_1"), _vertices("BA_1D_1")}:
        method = "center"
    elif pair == {_vertices("AB_1D_1"), _vertices("ACD_1")}:
        method = "altitudes"
    else:
        raise ContentPlanError("the cube linear-angle construction needs review")
    cosine = c.plane_cosine(p1, p2, (sp.S.One,) * 3)
    a = sp.Symbol("a", positive=True)
    p = c.points((a,) * 3)
    if method == "center":
        M = (p["A_1"] + p["B"]) / 2
        O = (p["A"] + p["C_1"]) / 2
        u = (O - M).norm()
        v = (p["C_1"] - M).norm()
        opposite = (O - p["C_1"]).norm()
    else:
        M = (p["A"] + p["D_1"]) / 2
        u = (p["B_1"] - M).norm()
        v = (p["C"] - M).norm()
        opposite = (p["B_1"] - p["C"]).norm()
    return model(
        "cube_projection_plane_angle",
        (),
        {
            "a": a,
            "first": u,
            "second": v,
            "opposite": opposite,
            "cosine": cosine,
            "face_diagonal": sp.sqrt(c.squared_length("AB_1", (a * a,) * 3)),
        },
        (method, claim, "cosine" if quantity == "косинус угла" else "angle"),
        cosine if quantity == "косинус угла" else sp.acos(cosine),
    )


def _box(groups):
    a, b, h = map(positive, groups[:3])
    quantity, pair = groups[3:]
    purpose = {
        "CDD_1 и BDA_1": "side",
        "ACD_1 и A_1B_1C_1": "top",
        "ABC и A_1DB": "base",
    }[pair]
    points = c.points((a, b, h))
    start, end, point = (
        ("B", "A_1", "A")
        if purpose == "side"
        else ("A", "C", "D")
        if purpose == "top"
        else ("B", "D", "A")
    )
    x, y, z = points[start], points[end], points[point]
    direction = y - x
    foot = x + direction * (z - x).dot(direction) / direction.dot(direction)
    helper = sp.simplify((z - foot).norm())
    numerator = b if purpose == "side" else h
    tan = sp.simplify(numerator / helper)
    q = {
        "a": a,
        "b": b,
        "height": h,
        "helper": helper,
        "numerator": numerator,
        "tan": tan,
        "cosine": 1 / sp.sqrt(1 + tan * tan),
        "E_x": foot[0],
        "E_y": foot[1],
        "E_z": foot[2],
        "hypotenuse": (y - x).norm(),
    }
    result = model(
        "box_parallel_plane_angle",
        (("a", a), ("b", b), ("height", h)),
        q,
        (purpose, "tangent" if quantity == "тангенс угла" else "angle"),
        tan if quantity == "тангенс угла" else sp.atan(tan),
    )
    return replace(result, squares=(a * a, b * b, h * h))


def read(raw):
    for claim, planes in CUBE_CLAIMS:
        match = re.fullmatch(CUBE + claim + CUBE_QUANTITY, raw)
        if match:
            return _cube(match.groups(), planes)
    match = re.fullmatch(BOX, raw)
    if match:
        try:
            return _box(match.groups())
        except UnsupportedCondition as exc:
            raise ContentPlanError(
                "complete positive box measurements are required"
            ) from exc
    return None
