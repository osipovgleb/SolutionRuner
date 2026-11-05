"""A right prism over a trapezoid, cut through a lateral-edge midpoint."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {"trapezoid_prism_pentagon_area"}
START = (
    r"(?:Дана прямая призма, в основании которой равнобедренная трапеция|[ВB] основании прямой призмы ABCDA_1B_1C_1D_1 лежит равнобедренная трапеция ABCD) "
    r"с основаниями AD\s*=\s*(.+?)(?: и|,) BC\s*=\s*(.+?)\. "
)
STANDARD = (
    r"Точка M делит ребро A_1D_1 в отношении A_1M\\colon MD_1\s*=\s*(.+?)\\colon\s*(.+?), (?:а )?точка K [—–-] середина (?:ребра )?DD_1\. "
    r"Докажите, что плоскость (?:MCK|MKC) делит отрезок BB_1 пополам\. "
    r"Найдите площадь сечения призмы плоскостью MKC, если "
    r"(?:\\angle ADC=60°, a \\angle MKC=90°|\\angle MKC=90° и \\angle ADC=60°)\."
)
RENAMED = (
    r"Точка G делит ребро A_1D_1 в отношении (.+?)(?:\\colon|:)\s*(.+?), считая от точки A_1, точка F [—–-] середина ребра DD_1\. "
    r"Докажите, что плоскость GFC делит ребро BB_1 пополам\. "
    r"Найдите площадь сечения призмы плоскостью GFC, если \\angle GFC=90°, \\angle ADC=60°\."
)


def read(raw):
    for pattern, names in ((STANDARD, ("M", "K")), (RENAMED, ("G", "F"))):
        match = re.fullmatch(START + pattern, raw)
        if not match:
            continue
        try:
            a, b, p, q = map(positive, match.groups())
        except UnsupportedCondition as exc:
            raise ContentPlanError(
                "complete numeric prism measurements are required"
            ) from exc
        if a <= b or sp.simplify(a * q / (p + q) - b) != 0:
            raise ContentPlanError("the upper-edge ratio must give MD1 equal to BC")
        d = a - b
        half_height = sp.sqrt(b * d / 2)
        length = sp.sqrt(b * b + half_height**2)
        width = sp.sqrt(d * d + half_height**2)
        return model(
            "trapezoid_prism_pentagon_area",
            tuple(zip(("a", "b", "p", "q"), (a, b, p, q), strict=True)),
            {
                "a": a,
                "b": b,
                "d": d,
                "p": p,
                "q": q,
                "HD": d / 2,
                "CH": d * sp.sqrt(3) / 2,
                "half_height": half_height,
                "length": length,
                "width": width,
                "EM": d * length / b,
                "cut_fraction": b / a,
                "diagonal_sq": b * b + d * d + b * d,
            },
            names,
            length * width * (1 + d / (2 * a)),
        )
    return None
