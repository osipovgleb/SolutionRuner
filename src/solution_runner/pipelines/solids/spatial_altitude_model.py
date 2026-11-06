"""Recognize complete pyramid altitude proofs and point-plane requests."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from .measurements import positive
from .pyramid_model import regular
from .spatial_metric_model import model

MODES = {
    "rectangular_pyramid_distance",
    "rectangular_pyramid_angle",
    "rectangular_pyramid_proved_altitude_angle",
    "square_midplane_distance",
    "triangle_face_distance",
}
RECTANGLE = (
    r"[ВB] основании четырехугольной пирамиды SABCD лежит прямоугольник ABCD со сторонами AB\s*=\s*(.+?) и BC\s*=\s*(.+?)\. "
    r"Длины боковых ребер пирамиды SA\s*=\s*(.+?),+ SB\s*=\s*(.+?),+ SD\s*=\s*(.+?)\. "
    r"Докажите, что SA [—–-] высота пирамиды\. Найдите (расстояние от вершины A до плоскости SBC|угол между прямой SC и плоскостью ASB|угол между прямыми SC и BD)\."
)
MIDPLANE = (
    r"Дана правильная четырехугольная пирамида SABCD\.? Боковое ребро SA\s*=\s*(.+?), сторона основания равна (.+?)\. "
    r"Докажите, что точки B и S равноудалены от плоскости ADM, где M [—–-] середина ребра SC\.? "
    r"Найдите расстояние от точки ([BS]) до плоскости ADM\.?"
)
FACE = (
    r"[ВB] правильной треугольной пирамиде SABC с основанием ABC боковое ребро равно (.+?), а сторона основания равна (.+?)\. "
    r"Докажите, что (AS\\perp BC|высоты пирамиды, проведенные из вершин A и S, пересекаются)\. "
    r"Найдите расстояние от вершины A до плоскости SBC\."
)


def _rectangle(groups):
    a, b, h, sb, sd = map(positive, groups[:5])
    if (
        sp.simplify(a * a + h * h - sb * sb) != 0
        or sp.simplify(b * b + h * h - sd * sd) != 0
    ):
        raise ContentPlanError(
            "the stated lateral edges do not prove SA is an altitude"
        )
    if groups[5] == "угол между прямыми SC и BD":
        return _rectangular_skew(a, b, h, sb, sd)
    angle = groups[5].startswith("угол")
    q = {
        "a": a,
        "b": b,
        "H": h,
        "SB": sb,
        "SD": sd,
        "SC": sp.sqrt(sb * sb + b * b),
        "tangent": b / sb,
    }
    answer = sp.atan(b / sb) * 180 / sp.pi if angle else a * h / sb
    return model(
        "rectangular_pyramid_angle" if angle else "rectangular_pyramid_distance",
        tuple(zip(("a", "b", "H", "SB", "SD"), (a, b, h, sb, sd), strict=True)),
        q,
        (),
        answer,
    )


def _rectangular_skew(a, b, h, sb, sd):
    diagonal = sp.sqrt(a * a + b * b)
    lateral = sp.sqrt(h * h + a * a + b * b)
    cosine = sp.simplify((b * b - a * a) / (diagonal * lateral))
    return model(
        "rectangular_pyramid_proved_altitude_angle",
        tuple(zip(("a", "b", "H", "SB", "SD"), (a, b, h, sb, sd), strict=True)),
        {
            "a": a,
            "b": b,
            "H": h,
            "SB": sb,
            "SD": sd,
            "AC": diagonal,
            "SC": lateral,
            "SE_squared": h * h + 4 * a * a,
            "BK": sp.sqrt(a * a + h * h / 4),
            "OB": diagonal / 2,
            "OK": lateral / 2,
            "cosine": cosine,
        },
        ("lines",),
        sp.acos(abs(cosine)),
    )


def _midplane(groups):
    e, a = map(positive, groups[:2])
    q = regular("square", {"a": a, "e": e})
    if sp.simplify(q["l"] - a) != 0:
        raise ContentPlanError(
            "the parent midpoint construction requires an equilateral section"
        )
    return model(
        "square_midplane_distance", (("e", e), ("a", a)), q, (groups[2],), a / 2
    )


def _face(groups):
    e, a = map(positive, groups[:2])
    q = regular("triangle", {"a": a, "e": e})
    q.update(foot=sp.simplify((e * e - a * a / 2) / (e * e - a * a / 4)))
    claim = "perpendicular" if groups[2].startswith("AS") else "altitudes"
    if claim == "altitudes" and q["H"] ** 2 < q["R"] ** 2 / 2:
        raise ContentPlanError(
            "the altitude segments do not intersect inside the pyramid"
        )
    return model(
        "triangle_face_distance",
        (("e", e), ("a", a)),
        q,
        (claim,),
        a * sp.sqrt(3) * q["H"] / (2 * q["l"]),
    )


def read(raw):
    for pattern, solve in (
        (RECTANGLE, _rectangle),
        (MIDPLANE, _midplane),
        (FACE, _face),
    ):
        match = re.fullmatch(pattern, raw)
        if match:
            return solve(match.groups())
    return None
