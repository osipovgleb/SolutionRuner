"""Symmetric tetrahedron projections and a regular-pyramid parallel rectangle."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .pyramid_model import root
from .spatial_metric_model import model
from .spatial_plane_model import parallel_cut_geometry

MODES = {
    "symmetric_tetrahedron_line_plane_angle",
    "triangle_pyramid_parallel_rectangle_distance",
}
CLAIM = r"Докажите, что (?:ребро SA перпендикулярно ребру BC|прямая SA перпендикулярна прямой BC)\. Найдите угол между прямой SA и плоскостью SBC\."
PARENT = (
    r"Дана пирамида SABC, в которой SC\s*=\s*SB\s*=\s*(.+?), AB\s*=\s*AC\s*=\s*(.+?), SA\s*=\s*BC\s*=\s*(.+?)\. "
    + CLAIM
)
VARIANT = (
    r"[ВB] пирамиде SABC известны длины ребер: AB\s*=\s*AC\s*=\s*(.+?), BC\s*=\s*SA\s*=\s*(.+?), SB\s*=\s*SC\s*=\s*(.+?)\. "
    + CLAIM
)
RECTANGLE = (
    r"[ВB] правильной треугольной пирамиде SABC точка P — делит сторону AB в отношении (.+?), считая от вершины A, "
    r"точка K — делит сторону BC в отношении (.+?), считая от вершины C\. Через точки P и K параллельно SB проведена плоскость \\omega\. "
    r"Докажите, что сечение пирамиды плоскостью \\omega является прямоугольником\. Найдите расстояние от точки S до плоскости \\omega, "
    r"если известно, что SC\s*=\s*(.+?), AC\s*=\s*(.+?)\."
)


def _symmetric(groups, variant):
    values = tuple(map(positive, groups))
    u, v, w = (values[2], values[0], values[1]) if variant else values
    sn = root(u * u - w * w / 4)
    an = root(v * v - w * w / 4)
    sm = sp.simplify((w * w + sn * sn - an * an) / (2 * sn))
    am = root(an * an - (sn - sm) ** 2)
    cosine = sp.simplify(abs(sm) / w)
    return model(
        "symmetric_tetrahedron_line_plane_angle",
        (("u", u), ("v", v), ("w", w)),
        {
            "u": u,
            "v": v,
            "w": w,
            "SN": sn,
            "AN": an,
            "x": sm,
            "SM": abs(sm),
            "NM": abs(sn - sm),
            "AM": am,
            "cosine": cosine,
            "foot": sm / sn,
        },
        (),
        sp.acos(cosine),
    )


def _rectangle(groups):
    first, second, e, a = map(positive, groups)
    if sp.simplify(first - second) != 0:
        raise ContentPlanError(
            "the two base-edge ratios do not give the stated parallel rectangle"
        )
    fraction = 1 / (1 + first)
    q = parallel_cut_geometry(a, e, fraction)
    q.update(
        ratio=first,
        BH=q["AH"],
        SH=q["l"],
        BT=a * a / (2 * e),
        HT=q["AH"] * q["H"] / e,
        point_fraction=1 - fraction,
    )
    return model(
        "triangle_pyramid_parallel_rectangle_distance",
        (("a", a), ("e", e), ("ratio", first)),
        q,
        (),
        q["distance"],
    )


def read(raw):
    for pattern, kind in (
        (PARENT, "parent"),
        (VARIANT, "variant"),
        (RECTANGLE, "rectangle"),
    ):
        match = re.fullmatch(pattern, raw)
        if match:
            try:
                return (
                    _rectangle(match.groups())
                    if kind == "rectangle"
                    else _symmetric(match.groups(), kind == "variant")
                )
            except UnsupportedCondition as exc:
                raise ContentPlanError(
                    "complete positive tetrahedron measurements and ratios are required"
                ) from exc
    return None
