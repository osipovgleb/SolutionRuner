"""Read midpoint, reflected-apex and median-section proofs in regular pyramids."""

import re
from dataclasses import replace

import sympy as sp

from ..core.errors import ContentPlanError
from ..word_problems.common import UnsupportedCondition
from .measurements import positive
from .pyramid_model import regular
from .spatial_metric_model import model

MODES = {
    "triangle_vertical_section_area",
    "reflected_triangle_section_midline",
    "reflected_square_section_midline",
    "square_median_section_area",
    "square_adjacent_midpoint_area",
}
VERTICAL = (
    r"[ВB] правильной треугольной пирамиде SABC сторона основания AB равна (.+?), а боковое ребро SA равно (.+?)\. "
    r"Точки M и N [—–-] середины ребер SA и SB соответственно\. Плоскость α содержит прямую MN и перпендикулярна плоскости основания пирамиды\. "
    r"Докажите, что плоскость α делит медиану C([EL]) основания в отношении (.+?):\s*(.+?), считая от точки C\. "
    r"Найдите площадь многоугольника, являющегося сечением пирамиды SABC плоскостью α\."
)
REFLECTED_TRIANGLE = (
    r"Все ребра правильной треугольной пирамиды SBCD с вершиной S равны (.+?)\. Основание O высоты SO этой пирамиды является серединой отрезка SS_1, "
    r"M [—–-] середина ребра SB, точка L лежит на ребре CD так, что CL:\s*LD\s*=\s*(.+?):\s*(.+?)\. "
    r"Докажите, что сечение пирамиды SBCD плоскостью S_1LM [—–-] (равнобедренная|равнобокая) трапеция\. Вычислите длину средней линии этой трапеции\."
)
REFLECTED_SQUARE = (
    r"Все ребра правильной четырехугольной пирамиды SABCD с вершиной S равны (.+?)\. Основание высоты SO этой пирамиды является серединой отрезка SS_1, "
    r"M [—–-] середина ребра AS, точка L лежит на ребре BC так, что BL:\s*LC\s*=\s*(.+?):\s*(.+?)\. "
    r"Докажите, что сечение пирамиды SABCD плоскостью S_1LM [—–-] (равнобедренная|равнобокая) трапеция\. Вычислите длину средней линии этой трапеции\."
)
MEDIAN_HEADER = r"[ВB] правильной четырехугольной пирамиде MABCD с вершиной M стороны основания равны (.+?), а боковые ребра равны (.+?)\. "
PERPENDICULAR = r"Докажите, что прямые MC и BD перпендикулярны\. "
MIDPOINT_REQUEST = r"Найдите площадь сечения пирамиды плоскостью, проходящей через точку B и середину ребра MD параллельно прямой AC\."
RATIO_REQUEST = (
    r"Докажите, что плоскость, проходящ(?:ая|ей) через точку B и середину ребра MD параллельно прямой AC, делит ребро MC в отношении (.+?):\s*(.+?), считая от вершины M\. "
    r"Найдите площадь сечения пирамиды этой плоскостью\."
)
POINT_REQUEST = (
    r"Точка N принадлежит ребру MC причем MN:\s*NC\s*=\s*(.+?):\s*(.+?)\. "
    + PERPENDICULAR
    + r"Найдите площадь сечения пирамиды плоскостью, проходящей через точки B и N параллельно прямой AC\."
)
ADJACENT_HEADER = r"[ВB] правильной четырехугольной пирамиде SABCD с основанием ABCD "
ADJACENT_FREE = r"проведено сечение через середины ребер AB и BC и вершину S\. "
ADJACENT_NAMED = r"через точки K и M [—–-] середины ребер AB и BC соответственно и вершину S проведено сечение\. "
ADJACENT_VOLUME = r"Докажите, что указанное сечение делит объем пирамиды в отношении (.+?):\s*(.+?)\. "
ADJACENT_RATIO = r"Докажите, что плоскость сечения делит отрезок DB в отношении (.+?):\s*(.+?), считая от вершины D\.? "
ADJACENT_PERP = r"Докажите, что прямые MK и SD перпендикулярны\. "
ADJACENT_ALL = r"Найдите площадь этого сечения, если все ребра пирамиды равны (.+?)\."
ADJACENT_GIVEN = r"Найдите площадь этого сечения, если боковое ребро пирамиды равно (.+?), а сторона основания равна (.+?)\."


def _adjacent(groups, kind, claim, equal):
    if claim != "perpendicular":
        p, q = map(positive, groups[:2])
        expected = sp.Rational(1, 7) if claim == "volume" else sp.Integer(3)
        if sp.simplify(p / q - expected) != 0:
            raise ContentPlanError(
                "the adjacent-midpoint section does not prove this ratio"
            )
        groups = groups[2:]
    e = positive(groups[0])
    a = e if equal else positive(groups[1])
    dims = regular("square", {"a": a, "e": e})
    dims.update(
        section_base=a / sp.sqrt(2),
        face_median=sp.sqrt(e * e - a * a / 4),
        section_height=sp.sqrt(e * e - 3 * a * a / 8),
    )
    result = model(
        "square_adjacent_midpoint_area",
        (("e", e), ("a", a)),
        dims,
        (kind, claim),
        dims["section_base"] * dims["section_height"] / 2,
    )
    return replace(result, squares=(a * a, e * e))


def _read_adjacent(raw):
    raw = raw.replace(r"\colon", ":")
    for intro, claim_pattern, kind, claim in (
        (ADJACENT_FREE, ADJACENT_VOLUME, "free", "volume"),
        (ADJACENT_FREE, ADJACENT_RATIO, "free", "diagonal_ratio"),
        (ADJACENT_NAMED, ADJACENT_PERP, "named", "perpendicular"),
    ):
        for measurements, equal in ((ADJACENT_ALL, True), (ADJACENT_GIVEN, False)):
            match = re.fullmatch(
                ADJACENT_HEADER + intro + claim_pattern + measurements, raw
            )
            if match:
                try:
                    return _adjacent(match.groups(), kind, claim, equal)
                except UnsupportedCondition as exc:
                    raise ContentPlanError(
                        "complete numeric section measurements are required"
                    ) from exc
    return None


def _vertical(groups):
    a, e = map(positive, groups[:2])
    label, p, q = groups[2:]
    if sp.simplify(positive(p) / positive(q) - 5) != 0:
        raise ContentPlanError(
            "the vertical midpoint plane divides the median in ratio 5:1"
        )
    dims = regular("triangle", {"a": a, "e": e})
    dims.update(
        median=sp.sqrt(3) * a / 2,
        lower=5 * a / 6,
        upper=a / 2,
        section_height=dims["H"] / 2,
    )
    return model(
        "triangle_vertical_section_area",
        (("a", a), ("e", e)),
        dims,
        (label,),
        a * dims["H"] / 3,
    )


def _reflected(groups, square):
    a = positive(groups[0])
    p, q = map(positive, groups[1:3])
    expected = sp.Rational(1, 2) if square else sp.Rational(7, 2)
    if sp.simplify(p / q - expected) != 0:
        raise ContentPlanError(
            "the reflected-apex section needs the stated parallel-base ratio"
        )
    dims = regular("square" if square else "triangle", {"a": a, "e": a})
    dims.update(lower=a if square else 7 * a / 9, upper=a / 2)
    return model(
        "reflected_square_section_midline"
        if square
        else "reflected_triangle_section_midline",
        (("a", a),),
        dims,
        (groups[3],),
        (dims["lower"] + dims["upper"]) / 2,
    )


def _median(groups, kind, claim):
    a, e = map(positive, groups[:2])
    if (
        len(groups) > 2
        and sp.simplify(positive(groups[2]) / positive(groups[3]) - 2) != 0
    ):
        raise ContentPlanError("this section cuts MC in ratio 2:1 from M")
    dims = regular("square", {"a": a, "e": e})
    dims.update(
        diagonal=sp.sqrt(2) * a,
        BE=sp.sqrt(4 * a * a + e * e) / 2,
        FG=2 * sp.sqrt(2) * a / 3,
    )
    return model(
        "square_median_section_area",
        (("a", a), ("e", e)),
        dims,
        (kind, claim),
        dims["BE"] * dims["FG"] / 2,
    )


def read(raw):
    raw = raw.replace(r"\alpha", "α")
    for pattern, solve in (
        (VERTICAL, _vertical),
        (REFLECTED_TRIANGLE, lambda g: _reflected(g, False)),
        (REFLECTED_SQUARE, lambda g: _reflected(g, True)),
        (
            MEDIAN_HEADER + PERPENDICULAR + MIDPOINT_REQUEST,
            lambda g: _median(g, "midpoint", "perpendicular"),
        ),
        (MEDIAN_HEADER + RATIO_REQUEST, lambda g: _median(g, "midpoint", "ratio")),
        (MEDIAN_HEADER + POINT_REQUEST, lambda g: _median(g, "point", "perpendicular")),
    ):
        match = re.fullmatch(pattern, raw)
        if match:
            return solve(match.groups())
    return _read_adjacent(raw)
