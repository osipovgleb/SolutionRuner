"""Three proof claims share one rhombus-prism section and linear angle."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {"rhombus_prism_section_angle"}
START = r"Дана прямая призма ABCDA_1B_1C_1D_1\. Основание призмы — ромб"
LENGTH = r" с острым углом A\s*=\s*(.+?)°\. Докажите, что AD_1\s*=\s*DB_1\. Найдите угол между плоскостью AC_1B и плоскостью ABD, если высота призмы равна (.+?), а ребро основания равно (.+?)\."
AREA = r" со стороной (.+?) и острым углом (.+?)°\. Высота призмы равна (.+?)\. Докажите, что площадь боковой поверхности призмы составляет более двух третей площади полной поверхности призмы\. Найдите угол между плоскостью AC_1B и плоскостью ABD\."
ANGLES = r"\. Докажите, что прямая A_1C образует с прямыми AB и AD равные углы\. Найдите угол между плоскостью AC_1B и плоскостью ABD, если известно, что сторона основания равна (.+?), острый угол основания равен (.+?)°, а высота призмы равна (.+?)\."


def read(raw):
    for pattern, claim in ((LENGTH, "length"), (AREA, "area"), (ANGLES, "line_angles")):
        match = re.fullmatch(START + pattern, raw)
        if not match:
            continue
        try:
            values = tuple(map(positive, match.groups()))
        except UnsupportedCondition as exc:
            raise ContentPlanError(
                "complete positive rhombus-prism measurements are required"
            ) from exc
        theta, h, a = values if claim == "length" else (values[1], values[2], values[0])
        if not 0 < theta < 90:
            raise ContentPlanError("the stated base angle must be acute")
        sine = sp.sin(theta * sp.pi / 180)
        cosine = sp.cos(theta * sp.pi / 180)
        if claim == "length" and sp.simplify(cosine - sp.Rational(1, 2)) != 0:
            raise ContentPlanError(
                "the claimed face diagonals are equal only for the stated equilateral base triangle"
            )
        if claim == "area" and sp.simplify(h - a * sine).is_positive is not True:
            raise ContentPlanError(
                "the lateral surface does not exceed two thirds of the total surface"
            )
        tan = h / (a * sine)
        return model(
            "rhombus_prism_section_angle",
            (("a", a), ("height", h), ("theta", theta)),
            {
                "a": a,
                "height": h,
                "theta": theta,
                "sine": sine,
                "cosine": cosine,
                "DH": a * sine,
                "diagonal": sp.sqrt(a * a + h * h),
                "lateral": 4 * a * h,
                "base_area": a * a * sine,
                "total": 4 * a * h + 2 * a * a * sine,
                "tan": tan,
                "margin_squared": h * h - a * a * sine * sine,
            },
            (claim,),
            sp.atan(tan),
        )
    return None
