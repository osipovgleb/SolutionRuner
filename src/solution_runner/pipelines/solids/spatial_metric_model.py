"""Shared regular-solid dimensions for midpoint sections and triangle altitudes."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from .measurements import positive
from .pyramid_model import regular, root

MODES = {
    "tetra_midpoint_distance",
    "hex_vertex_line_distance",
    "prism_plane_altitude",
    "prism_square_skew",
}
TRIANGLE = r"Дана правильная треугольная пирамида DABC с вершиной D\. "
MID_EDGE = (
    r"Боковое ребро пирамиды равно (.+?), высота равна (.+?)\. "
    r"Докажите, что сечение пирамиды, проходящее через середины ребер BD, AC и AD, является прямоугольником\. "
    r"Найдите расстояние от середины бокового ребра BD до прямой MT, где точки M и T [—–-] середины ребер AC и AD соответственно\."
)
MID_BASE = (
    r"Сторона основания пирамиды равна (.+?), высота равна (.+?)\. "
    r"Докажите, что сечение, проходящее через середину бокового ребра BD и точки M и T \(середины ребер AC и AB соответственно\), является прямоугольником\. "
    r"Найдите расстояние от середины бокового ребра BD до прямой MT\."
)
HEX = (
    r"[ВB] правильной шестиугольной пирамиде SABCDEF,? стороны основания (?:которой )?равны (.+?), а боковые ребра равны (.+?)\. "
    r"Докажите, что прямые S([A-F]) и ([A-F])([A-F]) перпендикулярны\. "
    r"Найдите расстояние от точки ([A-F]) до прямой S([A-F])\.?"
)
PRISM = (
    r"[ВB] правильной треугольной призме ABCA_1B_1C_1 высота равна (.+?), (?:сторона основания равна|а ребро основания равно) (.+?)\. "
    r"Докажите, что точки (A_1|A) и (B|B_1) равноудалены от плоскости (AB_1C_1|BA_1C_1|A_1BC_1)\. "
    r"Найдите расстояние от точки (B_1|A_1) до прямой (AC_1|BC_1)\."
)
SQUARE = (
    r"Дана правильная треугольная призма ABCA_1B_1C_1, все ребра основания которой равны (.+?)\. "
    r"Сечение, проходящее через боковое ребро AA_1 и середину M ребра B_1C_1, является квадратом\. "
    r"Докажите, что расстояние между прямыми A_1B и AM равно длине перпендикуляра, опущенного из центра этого квадрата на прямую A_1B\. Найдите это расстояние\."
)


def model(mode, given, q, names, answer):
    from .spatial_distance_model import SpatialDistance

    return SpatialDistance(
        mode,
        given,
        {k: sp.simplify(v) for k, v in q.items()},
        names,
        sp.simplify(answer),
    )


def _midpoint(groups, lateral):
    keys = ("e", "H") if lateral else ("a", "H")
    given = tuple(zip(keys, (positive(v) for v in groups), strict=True))
    q = regular("triangle", dict(given))
    return model(
        "tetra_midpoint_distance",
        given,
        q,
        ("AD" if lateral else "AB",),
        q["a" if lateral else "e"] / 2,
    )


def hex_points(a, h):
    points = {
        n: sp.Matrix([a * sp.cos(i * sp.pi / 3), a * sp.sin(i * sp.pi / 3), 0])
        for i, n in enumerate("ABCDEF")
    }
    return points | {"S": sp.Matrix([0, 0, h])}


def _hex(groups):
    a, e = map(positive, groups[:2])
    x, u, v, y, z = groups[2:]
    q = regular("hexagon", {"a": a, "e": e})
    points = hex_points(a, q["H"])
    if (
        u == v
        or y == z
        or sp.simplify((points[x] - points["S"]).dot(points[v] - points[u])) != 0
    ):
        raise ContentPlanError(
            "the named hexagon lines do not prove the claimed perpendicularity"
        )
    b = sp.simplify((points[y] - points[z]).norm())
    face = root(e * e - b * b / 4)
    q.update(b=b, face=face, foot=sp.simplify(1 - b * b / (2 * e * e)))
    return model(
        "hex_vertex_line_distance",
        (("a", a), ("e", e)),
        q,
        (x, u, v, y, z),
        b * face / e,
    )


def _prism(groups):
    h, a = map(positive, groups[:2])
    first, second, plane, target, line = groups[2:]
    names = (first, second, plane, target, line)
    if names not in {
        ("A_1", "B", "AB_1C_1", "B_1", "AC_1"),
        ("A", "B_1", "BA_1C_1", "A_1", "BC_1"),
        ("A", "B_1", "A_1BC_1", "A_1", "BC_1"),
    }:
        raise ContentPlanError(
            "the prism plane and requested altitude describe different constructions"
        )
    q = {
        "a": a,
        "H": h,
        "leg": root(a * a + h * h),
        "median": root(h * h + 3 * a * a / 4),
    }
    return model(
        "prism_plane_altitude",
        (("H", h), ("a", a)),
        q,
        ("A" if target == "B_1" else "B",),
        a * q["median"] / q["leg"],
    )


def _square(groups):
    a = positive(groups[0])
    h = sp.sqrt(3) * a / 2
    q = {"a": a, "H": h, "diagonal": sp.sqrt(2) * h, "leg": root(a * a + h * h)}
    return model(
        "prism_square_skew", (("a", a),), q, (), q["diagonal"] * a / (4 * q["leg"])
    )


def read(raw):
    for pattern, solve in (
        (TRIANGLE + MID_EDGE, lambda g: _midpoint(g, True)),
        (TRIANGLE + MID_BASE, lambda g: _midpoint(g, False)),
        (HEX, _hex),
        (PRISM, _prism),
        (SQUARE, _square),
    ):
        match = re.fullmatch(pattern, raw)
        if match:
            return solve(match.groups())
    return None
