"""A split lateral triangle determines a tetrahedral volume and a median section."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {"perpendicular_equilateral_triangle_volume"}
COLON = r"\s*(?::|\\colon)\s*"
QUESTION = (
    r"Правильные треугольники ABC и (ABM|MBC) лежат в перпендикулярных плоскостях, "
    r"(AB|BC)\s*=\s*(.+?)\. Точка P — середина (AM|CM),? а точка T делит отрезок BM так, что BT"
    + COLON
    + r"TM\s*=\s*(.+?)"
    + COLON
    + r"(.+?)\. Докажите, что (.+?)\. Вычислите объем пирамиды (MPTC|MPTA)\."
)
CUT = (
    r"плоскость (CPT|APT) делит высоту MD треугольника (AMB|BMC) в отношении (.+?)"
    + COLON
    + r"(.+?), считая от точки M"
)


def _claim(raw, u, r):
    if raw == r"CT\gt BP" and u == "C":
        if r == sp.Rational(1, 2):
            raise ContentPlanError("the midpoint makes CT equal to BP")
        return "inequality"
    claim = re.fullmatch(CUT, raw)
    if not claim:
        raise ContentPlanError(
            "the specified perpendicular-triangle claim is unsupported"
        )
    plane, triangle, left, right = claim.groups()
    expected = ("CPT", "AMB") if u == "A" else ("APT", "BMC")
    if (plane, triangle) != expected:
        raise ContentPlanError(
            "the section plane must contain the stated opposite vertex"
        )
    if sp.simplify(positive(left) / positive(right) - 2 * r) != 0:
        raise ContentPlanError(
            "the edge division does not give the claimed median ratio"
        )
    return "cut"


def read(raw):
    match = re.fullmatch(QUESTION, raw)
    if not match:
        return None
    triangle, edge, raw_a, midpoint, left, right, claim, solid = match.groups()
    u, apex = ("A", "C") if triangle == "ABM" else ("C", "A")
    expected = ("AB", "AM", "MPTC") if u == "A" else ("BC", "CM", "MPTA")
    if (edge, midpoint, solid) != expected:
        raise ContentPlanError("the shared edge, midpoint and volume apex must agree")
    try:
        a, p, q = map(positive, (raw_a, left, right))
        r = sp.simplify(q / (p + q))
        kind = _claim(claim, u, r)
    except UnsupportedCondition as exc:
        raise ContentPlanError(
            "positive exact triangle dimensions and division terms are required"
        ) from exc
    quantities = {
        "a": a,
        "MT_fraction": r,
        "BT_fraction": 1 - r,
        "ME_fraction": 2 * r / (1 + 2 * r),
        "cut_ratio": 2 * r,
        "height": a * sp.sqrt(3) / 2,
        "base_area": a * a * sp.sqrt(3) / 4,
        "area_fraction": r / 2,
        "section_area": a * a * sp.sqrt(3) * r / 8,
        "CT_squared": a * a * (1 - r + r * r),
        "BP_squared": 3 * a * a / 4,
        "difference": a * a * (r - sp.Rational(1, 2)) ** 2,
    }
    return model(
        "perpendicular_equilateral_triangle_volume",
        (("a", a), ("p", p), ("q", q)),
        quantities,
        (u, apex, kind),
        a**3 * r / 16,
    )
