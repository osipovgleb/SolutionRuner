"""Parallel similar triangles determine a section's midpoint and height."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {"parallelogram_prism_trapezoid_area"}
PATTERN = (
    r"(?:Основанием прямой призмы ABCDA_1B_1C_1D_1 является параллелограмм|[ВB] основании прямой призмы ABCDA_1B_1C_1D_1 лежит параллелограмм ABCD)\. "
    r"На ребрах A_1B_1, B_1C_1 и BC отмечены точки M, K и N соответственно, причем B_1K\\colon KC_1\s*=\s*(.+?)\\colon\s*(.+?)(?:, а|\. Четырехугольник) AMKN [—–-] равнобедренная трапеция с основаниями (.+?) и (.+?)\. "
    r"Докажите, что N [—–-] середина BC\. Найдите площадь трапеции AMKN, если объем призмы(?: ABCDA_1B_1C_1D_1)? равен (.+?), а ее высота равна (.+?)\."
)


def read(raw):
    match = re.fullmatch(PATTERN, raw)
    if not match:
        return None
    try:
        p, q, small, large, volume, height = map(positive, match.groups())
    except UnsupportedCondition as exc:
        raise ContentPlanError(
            "complete numeric prism measurements are required"
        ) from exc
    if small >= large:
        raise ContentPlanError(
            "the interior upper base must be shorter than the lower base"
        )
    ratio = small / large
    fraction = p / (p + q)
    if sp.simplify(fraction / ratio - sp.Rational(1, 2)) != 0:
        raise ContentPlanError("the given ratio does not prove the claimed midpoint")
    base = volume / height
    triangle = base / 4
    lower_height = 2 * triangle / large
    upper_height = ratio * lower_height
    section_height = sp.sqrt(height * height + (lower_height - upper_height) ** 2)
    return model(
        "parallelogram_prism_trapezoid_area",
        tuple(
            zip(
                ("p", "q", "small", "large", "volume", "height"),
                (p, q, small, large, volume, height),
                strict=True,
            )
        ),
        {
            "p": p,
            "q": q,
            "fraction": fraction,
            "ratio": ratio,
            "small": small,
            "large": large,
            "volume": volume,
            "height": height,
            "base": base,
            "triangle": triangle,
            "upper_triangle": ratio * ratio * triangle,
            "BH": lower_height,
            "B1H1": upper_height,
            "difference": lower_height - upper_height,
            "altitude": section_height,
        },
        (),
        (small + large) * section_height / 2,
    )
