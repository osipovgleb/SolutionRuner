"""Square-prism diagonal trapezoids and the reverse rhombus section."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {
    "square_prism_ratio_area",
    "square_prism_rhombus_height",
    "square_prism_rhombus_area",
}
TRAPEZOID = (
    r"[ВB] правильной четырехугольной призме ABCDA_1B_1C_1D_1 сторона основания равна (.+?), а боковое ребро AA_1\s*=\s*(.+?)\. "
    r"Точка ([MK]) принадлежит ребру (A_1D_1|B_1C_1) и делит его в отношении (.+?)(?:\\colon|:)\s*(.+?), считая от вершины (D_1|B_1)\. "
    r"Докажите, что сечение этой призмы плоскостью, проходящей через точки B, D и ([MK]), (?:является равнобедренной трапецией|есть равнобедренная трапеция)\. "
    r"Найдите площадь (?:этой трапеции|этого сечения)\."
)
RHOMBUS = (
    r"[ВB] правильной четырехугольной призме ABCDA_1B_1C_1D_1 плоскость α проходит через вершины B_1 и D, пересекает стороны AA_1 и CC_1 в точках M и K соответственно"
    r"(?:, а сечение призмы плоскостью α является ромбом|\. Известно, что четырехугольник MB_1KD [—–-] ромб)\. "
    r"Докажите, что точка M [—–-] середина ребра AA_1\. Найдите высоту призмы(?: ABCDA_1B_1C_1D_1)?, если площадь (?:ее )?основания(?: ABCD)? равна (.+?), а площадь (?:сечения|ромба MB_1KD) равна (.+?)\."
)
REVERSE = (
    r"[ВB] правильной четырехугольной призме ABCDA_1B_1C_1D_1 плоскость проходит через вершины B_1 и D и пересекает ребра AA_1 и CC_1 в точках M и K соответственно\. "
    r"Известно, что M [—–-] середина AA_1\. Докажите, что MB_1KD [—–-] ромб\. "
    r"Найдите площадь ромба MB_1KD, если объем призмы ABCDA_1B_1C_1D_1 равен (.+?), а площадь ее основания ABCD равна (.+?)\."
)


def _trapezoid(groups):
    a, h = map(positive, groups[:2])
    point, edge, p, q, start, claim = groups[2:]
    if (point, edge, start, claim) not in {
        ("M", "A_1D_1", "D_1", "M"),
        ("K", "B_1C_1", "B_1", "K"),
    }:
        raise ContentPlanError("the diagonal section point and ratio direction differ")
    p, q = positive(p), positive(q)
    t = q / (p + q)
    diagonal = a * sp.sqrt(2)
    upper = t * diagonal
    side = sp.sqrt(h * h + (a * (1 - t)) ** 2)
    offset = (diagonal - upper) / 2
    altitude = sp.sqrt(side * side - offset * offset)
    return model(
        "square_prism_ratio_area",
        (("a", a), ("height", h), ("p", p), ("q", q)),
        {
            "a": a,
            "height": h,
            "fraction": t,
            "diagonal": diagonal,
            "upper": upper,
            "edge_part": a * (1 - t),
            "side": side,
            "offset": offset,
            "altitude": altitude,
        },
        (point,),
        (diagonal + upper) * altitude / 2,
    )


def _rhombus(groups, reverse):
    first, second = map(positive, groups)
    base = second if reverse else first
    diagonal = sp.sqrt(2 * base)
    if reverse:
        h = first / base
        oblique = sp.sqrt(h * h + 2 * base)
        area = diagonal * oblique / 2
    else:
        area = second
        if area <= base:
            raise ContentPlanError("the rhombus area requires a positive prism height")
        oblique = 2 * area / diagonal
        h = sp.sqrt(oblique * oblique - 2 * base)
    return model(
        "square_prism_rhombus_" + ("area" if reverse else "height"),
        (("volume", first), ("base", base))
        if reverse
        else (("base", base), ("area", area)),
        {
            "base": base,
            "a": sp.sqrt(base),
            "diagonal": diagonal,
            "oblique": oblique,
            "height": h,
            "area": area,
        },
        (),
        area if reverse else h,
    )


def read(raw):
    raw = raw.replace(r"\alpha", "α")
    for pattern, kind in (
        (TRAPEZOID, "trapezoid"),
        (RHOMBUS, "rhombus"),
        (REVERSE, "reverse"),
    ):
        match = re.fullmatch(pattern, raw)
        if match:
            try:
                return (
                    _trapezoid(match.groups())
                    if kind == "trapezoid"
                    else _rhombus(match.groups(), kind == "reverse")
                )
            except UnsupportedCondition as exc:
                raise ContentPlanError(
                    "complete numeric prism measurements are required"
                ) from exc
    return None
