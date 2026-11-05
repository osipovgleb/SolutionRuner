"""One regular-prism trapezoid for perimeter, area and construction requests."""

import re
from dataclasses import replace

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {"triangle_prism_cut_area", "triangle_prism_cut_perimeter"}
CONSTRUCT = (
    r"[ВB] основании правильной треугольной призмы ABCA_1B_1C_1 лежит треугольник со стороной (.+?)\. "
    r"Высота призмы равна (.+?)\. Точка N [—–-] середина ребра A_1C_1\. "
    r"Постройте сечение призмы плоскостью BAN\. Найдите (периметр|площадь) этого сечения\."
)
PROVE = (
    r"[ВB] правильной треугольной призме ABCA_1B_1C_1 стороны основания равны (.+?), боковые ребра равны (.+?)\. "
    r"Изобразите сечение, проходящее через вершины A, ([BC]) и середину ребра (A_1[BC]_1), и докажите, что (?:это равнобокая трапеция|оно является равнобокой трапецией)\. "
    r"Найдите площадь этого сечения\."
)


def _solve(groups, kind, prime):
    a, h = map(positive, groups[:2])
    if kind == "construct":
        base, request = "AB", "perimeter" if groups[2] == "периметр" else "area"
    else:
        end, edge = groups[2:]
        if edge != ("A_1C_1" if end == "B" else "A_1B_1"):
            raise ContentPlanError(
                "the midpoint edge must connect the first and opposite base vertices"
            )
        base, request = "A" + end, "area"
    q = {
        "a": a,
        "height": h,
        "upper": a / 2,
        "side": sp.sqrt(h * h + a * a / 4),
        "offset": a / 4,
        "section_height": sp.sqrt(h * h + 3 * a * a / 16),
    }
    answer = (
        3 * a / 2 + 2 * q["side"]
        if request == "perimeter"
        else 3 * a * q["section_height"] / 4
    )
    result = model(
        "triangle_prism_cut_" + request,
        (("a", a), ("height", h)),
        q,
        (kind, base, "prime" if prime else "subscript"),
        answer,
    )
    return replace(result, symbols={"top": "'" if prime else "_1"})


def read(raw):
    prime = "ABCA'B'C'" in raw
    if prime:
        for letter in "ABC":
            raw = raw.replace(letter + "'", letter + "_1")
    for pattern, kind in ((CONSTRUCT, "construct"), (PROVE, "prove")):
        match = re.fullmatch(pattern, raw)
        if match:
            try:
                return _solve(match.groups(), kind, prime)
            except UnsupportedCondition as exc:
                raise ContentPlanError(
                    "complete numeric prism measurements are required"
                ) from exc
    return None
