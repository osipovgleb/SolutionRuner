"""Arc partitions and opposite-angle relations in cyclic polygons."""

import sympy as sp

from ..core.errors import ContentPlanError
from ..quadrilaterals.trapezoid.isosceles_model import DEGREE

RULES = {
    "circle-cyclic-opposite-angle": "cyclic_opposite",
    "circle-three-arc-ratio-largest-angle": "triangle_arc_ratio",
    "circle-cyclic-four-arcs-angle": "cyclic_four_arcs",
    "circle-cyclic-four-arc-ratio": "cyclic_arc_ratio",
    "circle-cyclic-angle-sum": "cyclic_sum",
    "circle-cyclic-angle-difference": "cyclic_difference",
    "circle-cyclic-unnamed-largest-angle": "cyclic_largest",
}
SEPARATOR = r"\s*(?::|\\colon)\s*"
PATTERNS = (
    (
        "cyclic_opposite",
        rf"Угол A\s+четырехугольника ABCD\s*,\s*вписанного в окружность, равен\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите угол C\s+этого четырехугольника",
    ),
    (
        "triangle_arc_ratio",
        r"Точки A\s*,\s*B\s*,\s*C\s*,\s*расположенные на окружности, делят ее на три дуги, градусные величины которых относятся как\s+(.+?)"
        + SEPARATOR
        + r"(.+?)"
        + SEPARATOR
        + r"(.+?)\s*\.\s*Найдите больший угол треугольника ABC",
    ),
    (
        "cyclic_four_arcs",
        rf"Стороны четырехугольника ABCD\s+AB\s*,\s*BC\s*,\s*CD\s+и\s+AD\s+стягивают дуги описанной окружности, градусные величины которых равны соответственно\s+(.+?)\s*{DEGREE}\s*,\s*(.+?)\s*{DEGREE}\s*,\s*(.+?)\s*{DEGREE}\s*,\s*(.+?)\s*{DEGREE}\s*\.\s*Найдите угол B\s+этого четырехугольника",
    ),
    (
        "cyclic_arc_ratio",
        r"Точки A\s*,\s*B\s*,\s*C\s*,\s*D\s*,\s*расположенные на окружности, делят эту окружность на четыре дуги AB\s*,\s*BC\s*,\s*CD\s+и\s+AD\s*,\s*градусные величины которых относятся соответственно как\s+(.+?)"
        + SEPARATOR
        + r"(.+?)"
        + SEPARATOR
        + r"(.+?)"
        + SEPARATOR
        + r"(.+?)\s*\.\s*Найдите угол A\s+четырехугольника ABCD",
    ),
    (
        "cyclic_sum",
        rf"Четырехугольник ABCD\s+вписан в окружность\s*\.\s*Угол ABD\s+равен\s+(.+?)\s*{DEGREE}\s*,\s*угол CAD\s+равен\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите угол ABC",
    ),
    (
        "cyclic_difference",
        rf"Четырехугольник ABCD\s+вписан в окружность\s*\.\s*Угол ABC\s+равен\s+(.+?)\s*{DEGREE}\s*,\s*угол ABD\s+равен\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите угол CAD",
    ),
    (
        "cyclic_largest",
        rf"Два угла вписанного в окружность четырехугольника равны\s+(.+?)\s*{DEGREE}\s+и\s+(.+?)\s*{DEGREE}\s*\.\s*Найдите больший из оставшихся углов(?: этого четырехугольника)?",
    ),
)


def solve(mode, given):
    if mode == "triangle_arc_ratio":
        return sp.simplify(180 * max(given) / sum(given))
    if mode == "cyclic_arc_ratio":
        return sp.simplify(180 * (given[1] + given[2]) / sum(given))
    if mode == "cyclic_four_arcs":
        if sum(given) != 360:
            raise ContentPlanError("four consecutive arcs must sum to 360 degrees")
        return (given[2] + given[3]) / 2
    if any(v >= 180 for v in given):
        raise ContentPlanError("cyclic interior angles must lie between 0 and 180")
    if mode == "cyclic_opposite":
        return 180 - given[0]
    if mode == "cyclic_sum":
        result = sum(given)
        if result >= 180:
            raise ContentPlanError(
                "the intercepted arcs must leave a positive remainder"
            )
    elif mode == "cyclic_difference":
        result = given[0] - given[1]
        if result <= 0:
            raise ContentPlanError("the whole angle must exceed its proper part")
    else:
        if sum(given) == 180:
            raise ContentPlanError(
                "the unnamed angles may be opposite; the others are undetermined"
            )
        result = 180 - min(given)
    return sp.simplify(result)
