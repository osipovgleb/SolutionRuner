"""One median cutting plane divides a regular triangular prism into equal volumes."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {"triangle_prism_half_volume_angle"}
QUESTION = (
    r"[ВB] правильной треугольной призме ABCA_1B_1C_1 стороны основания равны (.+?), боковые ребра равны (.+?), "
    r"точка D — середина ребра CC_1\. Докажите, что плоскость (?:ADB_1|AB_1D) делит объем призмы пополам\. "
    r"Найдите угол между плоскостями ABC и ADB_1\."
)


def read(raw):
    match = re.fullmatch(QUESTION, raw)
    if not match:
        return None
    try:
        a, h = map(positive, match.groups())
    except UnsupportedCondition as exc:
        raise ContentPlanError(
            "positive triangular-prism dimensions are required"
        ) from exc
    base_height = sp.sqrt(3) * a / 2
    base_area = a * base_height / 2
    trapezoid = 3 * a * h / 4
    return model(
        "triangle_prism_half_volume_angle",
        (("a", a), ("height", h)),
        {
            "a": a,
            "height": h,
            "half_height": h / 2,
            "base_height": base_height,
            "base_area": base_area,
            "trapezoid_area": trapezoid,
            "pyramid_volume": trapezoid * base_height / 3,
            "volume": base_area * h,
            "CH": a / 2,
            "tan": h / a,
        },
        (),
        sp.atan(h / a),
    )
