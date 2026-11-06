"""A vertical chord section is a rectangle whose far-side vertex gives a pyramid."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {"cylinder_chord_rectangle_pyramid_volume"}
FIRST = (
    r"[ВB] одном основании прямого кругового цилиндра с высотой (.+?) и радиусом основания (.+?) проведена хорда AB, равная радиусу основания, "
    r"а в другом его основании проведен диаметр CD, перпендикулярный AB\. "
    r"Построено сечение ABNM, проходящее через прямую AB перпендикулярно прямой CD так, что точка C и центр основания цилиндра, "
    r"в котором проведен диаметр CD, лежат с одной стороны от сечения\. "
    r"Докажите, что диагонали этого сечения равны между собой\. Найдите объем пирамиды CABNM\."
)
SECOND = (
    r"Дан прямой круговой цилиндр высотой (.+?) и радиусом (.+?)\. "
    r"[ВB] одном из оснований проведена хорда AB, равная радиусу основания, а в другом основании проведен диаметр CD, перпендикулярный прямой AB\. "
    r"Построено сечение цилиндра плоскостью ABNM, перпендикулярной прямой CD, причем точка C и центр основания цилиндра, "
    r"содержащего отрезок CD, лежат по одну сторону от плоскости сечения\. "
    r"Докажите, что диагонали четырехугольника ABNM равны\. Найдите объем пирамиды CABNM\."
)


def read(raw):
    for pattern in (FIRST, SECOND):
        match = re.fullmatch(pattern, raw)
        if not match:
            continue
        try:
            h, radius = map(positive, match.groups())
        except UnsupportedCondition as exc:
            raise ContentPlanError(
                "positive exact cylinder radius and height are required"
            ) from exc
        offset = sp.sqrt(3) * radius / 2
        return model(
            "cylinder_chord_rectangle_pyramid_volume",
            (("H", h), ("R", radius)),
            {
                "H": h,
                "R": radius,
                "half_chord": radius / 2,
                "section_area": h * radius,
                "offset": offset,
                "pyramid_height": radius + offset,
            },
            (),
            h * radius * (radius + offset) / 3,
        )
    return None
