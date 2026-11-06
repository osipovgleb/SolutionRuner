"""A cube cut parallel to a space diagonal: edge ratio, angle or volume."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .spatial_metric_model import model

MODES = {"cube_parallel_cut_angle", "cube_parallel_cut_volume"}
START = (
    r"(?:[ВB] кубе ABCDA_1B_1C_1D_1 все ребра равны (.+?)\. На его ребре|Ребро куба ABCDA_1B_1C_1D_1 равно (.+?)\. На ребре) "
    r"BB_1 отмечена точка K так[,.] что KB\s*=\s*(.+?)\. Через точки K и C_1 (?:построена|проведена) плоскость α, параллельная прямой BD_1\. "
    r"Докажите, что A_1P\s*(?:\\colon|:)\s*PB_1\s*=\s*(.+?)\s*(?:\\colon|:)\s*(.+?), где P — точка пересечения плоскости α с ребром A_1B_1\. "
)
ANGLE = r"Найдите (?:угол наклона плоскости α к плоскости грани BB_1C_1C|угол между плоскостями α и BB_1C_1)\."
VOLUME = (
    r"Найдите объем большей из двух частей куба, на которые он делится плоскостью α\."
)


def read(raw):
    raw = raw.replace(r"\alpha", "α")
    for ending, quantity in ((ANGLE, "angle"), (VOLUME, "volume")):
        match = re.fullmatch(START + ending, raw)
        if not match:
            continue
        first, second, edge_point, p, q = match.groups()
        try:
            a, k, p, q = map(positive, (first or second, edge_point, p, q))
        except UnsupportedCondition as exc:
            raise ContentPlanError(
                "complete positive cube measurements are required"
            ) from exc
        if not a / 2 < k < a:
            raise ContentPlanError(
                "the triangular cube section requires an interior top-edge point"
            )
        d = a - k
        ratio = (2 * k - a) / d
        if sp.simplify(ratio - p / q) != 0:
            raise ContentPlanError("the claimed top-edge ratio does not follow from KB")
        tan = sp.sqrt(a * a + d * d) / k
        small = a * a * d * d / (6 * k)
        values = {
            "a": a,
            "k": k,
            "d": d,
            "p": p,
            "q": q,
            "ratio": ratio,
            "B1P": a * d / k,
            "A1P": a * (2 * k - a) / k,
            "B1L": d * sp.sqrt(2),
            "D1M": d * sp.sqrt(2),
            "ML": (2 * k - a) * sp.sqrt(2),
            "KC1": sp.sqrt(a * a + d * d),
            "triangle_area": a * d / 2,
            "B1N": a * d / sp.sqrt(a * a + d * d),
            "tan": tan,
            "cos": k / sp.sqrt(d * d + k * k + a * a),
            "small_volume": small,
            "large_volume": a**3 - small,
        }
        return model(
            "cube_parallel_cut_" + quantity,
            (("a", a), ("k", k), ("p", p), ("q", q)),
            values,
            (),
            sp.atan(tan) if quantity == "angle" else a**3 - small,
        )
    return None
