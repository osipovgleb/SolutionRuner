"""Menelaus sections and inverse perpendicular-section areas in pyramids."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {"pyramid_midline_ratio", "square_perpendicular_section_ratio"}
PARENT = (
    r"Дана правильная пирамида SABC с основанием ABC, точки K и M [—–-] середины ребер AB и SC соответственно\. "
    r"Точки N и L на сторонах BC и SA соответственно расположены таким образом, что LA\s*=\s*(.+?)\s*SL и прямые NL и MK пересекаются\. "
    r"Докажите, что прямые LK, MN и BS пересекаются в одной точке\. Найдите отношение CN\\colon NB\."
)
STANDARD = (
    r"Дана правильная пирамида SABC, точки M и K [—–-] середины ребер AB и SC соответственно\. "
    r"Точки N и L на сторонах SA и BC соответственно расположены таким образом, что AN\s*=\s*(.+?)\s*NS и прямые NL и MK пересекаются\. "
    r"Докажите, что прямые LK, MN и BS пересекаются в одной точке\. Найдите отношение BL\\colon LC\."
)
WEIGHTED = (
    r"[ВB] правильной треугольной пирамиде SABC с основанием ABC точки M и K [—–-] середины ребер AB и SC соответственно, "
    r"а точки N и L отмечены на ребрах SA и BC соответственно так, что отрезки MK и NL пересекаются, а (.+?)\s*AN\s*=\s*(.+?)\s*NS\. "
    r"Докажите, что прямые MN, KL и SB пересекаются в одной точке\. Найдите отношение BL\\colon LC\."
)
EXTERNAL = (
    r"[ВB] правильной треугольной пирамиде SABC с основанием ABC точки M и K [—–-] середины ребер AB и SC соответственно\. "
    r"На продолжении ребра SB за точку S отмечена точка R\. Прямые RM и RK пересекают ребра AS и BC в точках N и L соответственно, причем (.+?)\s*BL\s*=\s*(.+?)\s*LC\. "
    r"Докажите, что прямые MK и NL пересекаются\. Найдите отношение AN\\colon NS\."
)
INVERSE = (
    r"[ВB] правильной четырехугольной пирамиде SABCD (?:известно, что AB|сторона основания AB)\s*=\s*(.+?)\. "
    r"Через точку O пересечения диагоналей основания перпендикулярно ребру SC провели плоскость α\. "
    r"Докажите, что плоскость α проходит через вершины B и D\. "
    r"(?:[ВB] каком отношении|Найдите, в каком отношении) плоскость α делит ребро SC, считая от вершины S, если площадь сечения равна (.+?)\s*\??\.?(?: ?\?)?"
)


def _midline(groups, kind):
    given = tuple(positive(v) for v in groups)
    ratio = sp.simplify(given[0] if len(given) == 1 else given[1] / given[0])
    if ratio == 1:
        raise ContentPlanError(
            "the midpoint lines are parallel to SB, with no finite common point"
        )
    if kind == "external" and ratio <= 1:
        raise ContentPlanError(
            "the stated external point beyond S requires a ratio greater than one"
        )
    parent = kind == "parent"
    names = (
        "external" if kind == "external" else "concurrent",
        "K" if parent else "M",
        "M" if parent else "K",
        "L" if parent else "N",
        "N" if parent else "L",
        "CN/NB" if parent else "AN/NS" if kind == "external" else "BL/LC",
    )
    return model(
        "pyramid_midline_ratio",
        tuple(
            zip(
                ("ratio",) if len(given) == 1 else ("left", "right"), given, strict=True
            )
        ),
        {"ratio": ratio, "inverse": 1 / ratio},
        names,
        1 / ratio if parent else ratio,
    )


def _inverse(groups):
    a, area = map(positive, groups)
    if area >= a * a / 2:
        raise ContentPlanError(
            "the perpendicular section area must be less than half the square base"
        )
    diagonal = a * sp.sqrt(2)
    oh = 2 * area / diagonal
    hc = sp.sqrt(a * a / 2 - oh * oh)
    edge = sp.simplify(a * a / (2 * hc))
    return model(
        "square_perpendicular_section_ratio",
        (("a", a), ("area", area)),
        {
            "a": a,
            "area": area,
            "diagonal": diagonal,
            "OC": a / sp.sqrt(2),
            "OH": oh,
            "HC": hc,
            "SC": edge,
            "SH": edge - hc,
            "height": sp.sqrt(edge * edge - a * a / 2),
        },
        (),
        (edge - hc) / hc,
    )


def read(raw):
    raw = raw.replace(r"\alpha", "α")
    for pattern, kind in (
        (PARENT, "parent"),
        (STANDARD, "standard"),
        (WEIGHTED, "weighted"),
        (EXTERNAL, "external"),
        (INVERSE, "inverse"),
    ):
        match = re.fullmatch(pattern, raw)
        if match:
            try:
                return (
                    _inverse(match.groups())
                    if kind == "inverse"
                    else _midline(match.groups(), kind)
                )
            except UnsupportedCondition as exc:
                raise ContentPlanError(
                    "complete numeric section measurements are required"
                ) from exc
    return None
