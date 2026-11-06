"""The squared-radius difference transfers one parallel spherical-section area."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {"concentric_sphere_parallel_section_area"}
QUESTION = (
    r"Плоскость α пересекает два шара, имеющих общий центр\. "
    r"Площадь сечения меньшего шара этой плоскостью равна (.+?)\. "
    r"Плоскость β, параллельная плоскости α, касается меньшего шара, а площадь сечения этой плоскостью большего шара равна (.+?)\. "
    r"Докажите, что сечение шара плоскостью(?: α)? есть круг\. "
    r"Найдите площадь сечения большего шара плоскостью α\."
)


def read(raw):
    match = re.fullmatch(QUESTION, raw)
    if not match:
        return None
    try:
        first, second = (positive(x, pi=True) for x in match.groups())
    except UnsupportedCondition as exc:
        raise ContentPlanError(
            "two positive exact spherical-section areas are required"
        ) from exc
    return model(
        "concentric_sphere_parallel_section_area",
        (("alpha_area", first), ("beta_area", second)),
        {
            "alpha_area": first,
            "beta_area": second,
            "FD_squared": first / sp.pi,
            "AB_squared": second / sp.pi,
            "CF_squared": (first + second) / sp.pi,
        },
        (),
        first + second,
    )
