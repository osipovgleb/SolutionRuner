"""Regular triangular-pyramid face angles from one face-to-base cosine."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .pyramid_model import regular
from .spatial_metric_model import model

MODES = {"triangle_pyramid_face_cosine_angle"}
OPPOSITE = r"Докажите, что ее противоположные ребра перпендикулярны\. "
REQUEST = r"Найдите угол между боковыми гранями этой пирамиды"
QUESTION = (
    r"Дана правильная треугольная пирамида\. "
    + OPPOSITE
    + r"Пусть (?:известно, что )?косинус угла между боковой гранью и основанием равен (.+?)\. "
    + REQUEST
    + r"\."
)
NAMED = (
    r"Дана правильная треугольная пирамида SABC с вершиной S\. Точка M — середина BC\. "
    r"Косинус угла между боковой гранью и основанием пирамиды равен (.+?)\. "
    + OPPOSITE
    + REQUEST
    + r", если SM\s*=\s*(.+?)\."
)


def _solve(groups):
    rho = positive(groups[0])
    if not rho < 1:
        raise ContentPlanError(
            "the face-to-base cosine must lie strictly between zero and one"
        )
    scale = sp.S.One if len(groups) == 2 else sp.Symbol("a", positive=True)
    apothem = positive(groups[1]) if len(groups) == 2 else sp.denom(rho) * scale
    edge = 2 * sp.sqrt(3) * apothem * rho
    q = regular("triangle", {"a": edge, "l": apothem})
    cosine = sp.simplify((1 - 3 * rho * rho) / 2)
    q.update(
        rho=rho,
        scale=scale,
        apothem=apothem,
        MH=apothem * rho,
        AM=3 * apothem * rho,
        CK=edge * apothem / q["e"],
        cosine=cosine,
        foot=(1 - 3 * rho * rho) / (1 + 3 * rho * rho),
    )
    given = (("rho", rho),) + ((("apothem", apothem),) if len(groups) == 2 else ())
    return model(
        "triangle_pyramid_face_cosine_angle",
        given,
        q,
        ("measured" if len(groups) == 2 else "scaled",),
        sp.acos(abs(cosine)),
    )


def read(raw):
    for pattern in (QUESTION, NAMED):
        match = re.fullmatch(pattern, raw)
        if match:
            try:
                return _solve(match.groups())
            except UnsupportedCondition as exc:
                raise ContentPlanError(
                    "an exact positive face cosine and apothem are required"
                ) from exc
    return None
