"""Edge-point sections in equilateral-base pyramids with a lateral altitude."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .pyramid_model import root
from .spatial_metric_model import model

MODES = {"right_triangle_pyramid_cut_area"}
PARENT = (
    r"[ВB] треугольной пирамиде MABC основанием является правильный треугольник ABC ребро MB перпендикулярно плоскости основания, стороны основания равны (.+?), а ребро MA\s*=\s*(.+?)\. "
    r"На ребре AC находится точка D, на ребре AB [—–-] точка E, а на ребре AM [—–-] точка L\. "
    r"Известно, что AD\s*=\s*AL\s*=\s*(.+?), и BE\s*=\s*(.+?)\. "
    r"Докажите, что ADE [—–-] равносторонний треугольник\. "
)
MIDPOINT = (
    r"[ВB] треугольной пирамиде MABC, в основаниии которой лежит правильный треугольник ABC, ребро MB перпендикулярно плоскости основания, стороны основания равны (.+?), а ребро MA равно (.+?)\. "
    r"На ребре AC находится точка D, на ребре AB точка E, а на ребре AM [—–-] точка F\. "
    r"Известно, что AD\s*=\s*(.+?) и BE\s*=\s*(.+?), F [—–−-] середина AM\. "
    r"Докажите, что треугольник ADE [—–−-] равносторонний\. "
)
APEX_A = (
    r"[ВB] треугольной пирамиде MABC с основанием ABC ребро MA перпендикулярно плоскости основания, стороны основания равны (.+?), а ребро MB равно (.+?)\. "
    r"На ребре AC находится точка D, на ребре AB точка E, а на ребре AM [—–-] точка L\. "
    r"Известно, что AD\s*=\s*(.+?) и BE\s*=\s*ML\s*=\s*(.+?)\. "
    r"Докажите, что LDE [—–-] равнобедренный треугольник\. "
)
REQUEST = r"Найдите площадь сечения пирамиды плоскостью, проходящей через точки E, D и {point}\."


def _solve(groups, kind):
    a, e, t, be = map(positive, groups)
    h = root(e * e - a * a)
    ma = h if kind == "A" else e
    al = ma - be if kind == "A" else ma / 2 if kind == "midpoint" else t
    if not (0 < t < a and 0 < be < a and 0 < al < ma):
        raise ContentPlanError("D, E and the cut point must lie inside the three edges")
    if sp.simplify(t - (a - be)) != 0:
        raise ContentPlanError(
            "the claimed equilateral or isosceles triangle requires AD=AE"
        )
    ld2 = al * al + t * t - (0 if kind == "A" else t * al * a / ma)
    le2 = al * al + t * t - (0 if kind == "A" else 2 * t * al * a / ma)
    cosine = sp.simplify((le2 + t * t - ld2) / (2 * sp.sqrt(le2) * t))
    section_height = root(le2 - ((le2 + t * t - ld2) / (2 * t)) ** 2)
    q = {
        "a": a,
        "e": e,
        "H": h,
        "MA": ma,
        "AD": t,
        "AE": t,
        "BE": be,
        "AL": al,
        "fraction": al / ma,
        "LD2": ld2,
        "LE2": le2,
        "DE2": t * t,
        "LD": sp.sqrt(ld2),
        "LE": sp.sqrt(le2),
        "DE": t,
        "cosine_E": cosine,
        "sine_E": section_height / sp.sqrt(le2),
        "section_height": section_height,
        "FK": al * h / ma,
        "KE": abs(t - al * a / ma),
        "KN": abs(t - al * a / ma) * sp.sqrt(3) / 2,
        "foot": (t - al * a / ma) / (2 * t),
    }
    return model(
        "right_triangle_pyramid_cut_area",
        (("a", a), ("e", e), ("AD", t), ("BE", be)),
        q,
        ("A" if kind == "A" else "B", "F" if kind == "midpoint" else "L", kind),
        t * section_height / 2,
    )


def read(raw):
    for pattern, kind, point in (
        (PARENT, "given", "L"),
        (MIDPOINT, "midpoint", "F"),
        (APEX_A, "A", "L"),
    ):
        match = re.fullmatch(pattern + REQUEST.format(point=point), raw)
        if match:
            try:
                return _solve(match.groups(), kind)
            except UnsupportedCondition as exc:
                raise ContentPlanError(
                    "complete numeric section measurements are required"
                ) from exc
    return None
