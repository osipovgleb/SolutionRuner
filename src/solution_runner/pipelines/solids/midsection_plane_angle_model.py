"""Common perpendiculars, opposite vertices and midpoint-section plane angles."""

import re

import sympy as sp

from .measurements import positive
from .pyramid_model import regular
from .spatial_metric_model import model

MODES = {
    "box_skew_distance_normal_angle",
    "square_prism_opposite_vertex_plane_angle",
    "triangle_pyramid_midpoint_plane_angle",
}

BOX = (
    r"Основание прямой четырехугольной призмы ABCDA_1B_1C_1D_1 — прямоугольник ABCD, в котором AB\s*=\s*(.+?), AD\s*=\s*(.+?)\. "
    r"Докажите, что расстояние между прямыми AC и B_1D_1 равно расстоянию между прямыми (?:A_1D_1 и BD|BD и A_1D_1)\. "
    r"Найдите угол между плоскостью основания призмы и плоскостью, проходящей через середину ребра AD перпендикулярно прямой BD_1, "
    r"если расстояние между прямыми AC и B_1D_1 равно (.+?)\."
)
SQUARE = (
    r"[ВB] правильной четырехугольной призме ABCDA_1B_1C_1D_1 стороны основания равны (.+?), а боковые ребра равны (.+?)\. "
    r"На ребре AA_1 отмечена точка E так, что AE:\s*EA_1\s*=\s*(.+?):\s*(.+?)\. "
    r"Докажите, что (?:точки A и C_1|вершины A_1 и C) равноудалены от плоскости BED_1\. Найдите угол между плоскостями ABC и BED_1\."
)
MIDPOINT = (
    r"Дана правильная треугольная пирамида SABC, AB\s*=\s*(.+?), высота SH, проведенная к основанию, равна (.+?), "
    r"точка K — середина AS, точка N — середина BC\. Плоскость, проходящая через точку K и параллельная основанию пирамиды, "
    r"пересекает ребра SB и SC в точках Q и P соответственно\. Докажите, что PQ проходит через середину отрезка SN\. "
    r"Найдите угол между плоскостью основания и плоскостью APQ\."
)
MIDPOINT_NAMED = (
    r"[ВB] правильной треугольной пирамиде SABC сторона основания AB равна (.+?), высота SH равна (.+?)\. "
    r"Точка K — середина бокового ребра SA, а точка N — середина ребра BC\. Плоскость, параллельная плоскости ABC, "
    r"проходит через точку K и пересекает ребра SB и SC в точках Q и P соответственно\. "
    r"Докажите, что прямая QP пересекает отрезок SN в его середине\. Найдите угол между плоскостями ABC и AQP\."
)


def _read(raw):
    match = re.fullmatch(BOX, raw)
    if match:
        a, b, h = map(positive, match.groups())
        base = sp.sqrt(a * a + b * b)
        tan = base / h
        return model(
            "box_skew_distance_normal_angle",
            (("a", a), ("b", b), ("height", h)),
            {"a": a, "b": b, "height": h, "base_diagonal": base, "tan": tan},
            (),
            sp.atan(tan),
        )
    match = re.fullmatch(SQUARE, raw)
    if match:
        a, h, p, q = map(positive, match.groups())
        e = h * p / (p + q)
        top = h - e
        ak = a * e / top
        bk = sp.sqrt(a * a + ak * ak)
        ah = a * ak / bk
        tan = e / ah
        return model(
            "square_prism_opposite_vertex_plane_angle",
            (("a", a), ("height", h), ("p", p), ("q", q)),
            {
                "a": a,
                "height": h,
                "AE": e,
                "A1E": top,
                "AK": ak,
                "BK": bk,
                "AH": ah,
                "tan": tan,
                "fraction": e / h,
            },
            ("A_1", "C") if "вершины A_1 и C" in raw else ("A", "C_1"),
            sp.atan(tan),
        )
    for pattern in (MIDPOINT, MIDPOINT_NAMED):
        match = re.fullmatch(pattern, raw)
        if match:
            a, h = map(positive, match.groups())
            q = regular("triangle", {"a": a, "H": h})
            an = a * sp.sqrt(3) / 2
            hn = an / 3
            sn = sp.sqrt(h * h + hn * hn)
            rn = sn / 2
            at = an - hn / 2
            rt = h / 2
            ar = sp.sqrt(at * at + rt * rt)
            tan = rt / at
            q.update(
                AN=an, HN=hn, SN=sn, RN=rn, AT=at, RT=rt, AR=ar, cosine=at / ar, tan=tan
            )
            return model(
                "triangle_pyramid_midpoint_plane_angle",
                (("a", a), ("height", h)),
                q,
                (),
                sp.acos(q["cosine"]),
            )
    return None


def read(raw):
    from ..core.errors import ContentPlanError
    from ..word_problems.common import UnsupportedCondition

    try:
        return _read(raw)
    except UnsupportedCondition as exc:
        raise ContentPlanError(
            "complete positive plane-angle measurements are required"
        ) from exc
