"""Complete projection, section and plane-angle questions in regular solids."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from .measurements import positive
from .pyramid_model import regular, root
from .spatial_metric_model import hex_points, model

MODES = {
    "prism_projection_height",
    "pyramid_skew_height",
    "hex_prism_distance",
    "ratio_plane_distance",
    "ratio_plane_angle",
}
PROJECTION = (
    r"[ВB] основании прямой призмы ABCA_1B_1C_1 лежит прямоугольный треугольник ABC, у которого угол C равен 90°, угол A равен (.+?)°, AC\s*=\s*(.+?)\. "
    r"Диагональ боковой грани B_1C составляет угол (.+?)° с плоскостью AA_1B_1\. (?:Отрезок )?CE [—–−-] высота треугольника ABC\. "
    r"Докажите, что угол B_1EC (?:[—–-] )?прямой\. Найдите высоту призмы\."
)
RENAMED = (
    r"Основанием прямой призмы MNKM_1N_1K_1 является прямоугольный треугольник MNK, у которого угол N равен 90°, угол M равен (.+?)°, NK\s*=\s*(.+?)\. "
    r"Диагональ боковой грани M_1N составля(?:ет|ют) угол (.+?)° с плоскостью MM_1K_1\. NE [—–−-] высота треугольника NKM\. "
    r"Докажите, что \\angle NM_1E\s*=\s*(.+?)°\.? Найдите высоту призмы\."
)
TANGENT = (
    r"Дана правильная четырехугольная пирамида MABCD, ребра основания которой равны (.+?)\. "
    r"Тангенс угла между прямыми DM и AL равен (.+?), L [—–-] середина ребра MB\. "
    r"Докажите, что плоскости ACL и MDB перпендикулярны\. Найдите высоту данной пирамиды\."
)
HEX_HEADER = r"[ВB] правильной шестиугольной призме ABCDEFA_1B_1C_1D_1E_1F_1"
HEX_GIVEN = (
    (r" стороны основания равны (.+?), а боковые ребра равны (.+?)\.", False),
    (r", все ребра которой равны (.+?)\.", True),
)
HEX_REQUEST = (
    r" Докажите, что плоскости ([A-F][A-F]_1[A-F]_1) и ([A-F][A-F][A-F]_1) перпендикулярны\. "
    r"Найдите расстояние от точки ([A-F]) до прямой ([A-F])_1([A-F])_1\."
)
RATIO_HEADER = (
    r"[ВB] правильной треугольной пирамиде SABC сторона основания AB\s*(?:равна|=)\s*(.+?), а боковое ребро SA\s*(?:равно|=)\s*(.+?)\. "
    r"На ребрах AB и SC отмечены точки K и M соответственно, причем AK\s*:\s*KB\s*=\s*SM\s*:\s*MC\s*=\s*(.+?)\s*:\s*(.+?)\. "
)
RATIO_DISTANCE = (
    r"Плоскость α содержит прямую KM и параллельна (?:прямой )?SA\. "
    r"Докажите, что плоскость α делит ребро (SB|AC) в отношении (.+?)\s*:\s*(.+?), считая от вершины (S|A)\. "
    r"Найдите расстояние между прямыми SA и KM\."
)
RATIO_ANGLE = (
    r"Плоскость α содержит прямую KM и параллельна прямой BC\. Докажите, что плоскость α параллельна прямой SA\. "
    r"Найдите угол между плоскостями α и SBC\."
)


def _projection(groups, renamed):
    angle, c, beta = (positive(v) for v in groups[:3])
    alpha = 90 - angle if renamed else angle
    if not (0 < alpha < 90 and 0 < beta < 90 - alpha):
        raise ContentPlanError("the prism angles must determine a positive height")
    if renamed and positive(groups[3]) != beta:
        raise ContentPlanError(
            "the claimed projection angle differs from the given line-plane angle"
        )
    sine = sp.sin(sp.pi * alpha / 180)
    cosine = sp.cos(sp.pi * alpha / 180)
    sb = sp.sin(sp.pi * beta / 180)
    cb = sp.cos(sp.pi * beta / 180)
    b = sp.simplify(c * sine / cosine)
    ce = sp.simplify(c * sine)
    be = sp.simplify(b * sine)
    height = root(ce * ce / (sb * sb) - b * b)
    q = {
        "c": c,
        "a_angle": alpha,
        "given_angle": angle,
        "beta": beta,
        "BC": b,
        "CE": ce,
        "BE": be,
        "H": height,
        "sin": sine,
        "cos": cosine,
        "sin_beta": sb,
        "cos_beta": cb,
        "diagonal": sp.simplify(ce / sb),
    }
    names = ("K", "M", "N", "angle") if renamed else ("A", "B", "C", "right")
    return model(
        "prism_projection_height",
        (("c", c), ("angle", angle), ("beta", beta)),
        q,
        names,
        height,
    )


def _tangent(groups):
    a, t = map(positive, groups)
    if not t < 2:
        raise ContentPlanError(
            "the tangent must determine a nondegenerate square pyramid"
        )
    q = regular("square", {"a": a, "e": sp.sqrt(2) * a / t})
    q.update(tangent=t, OL=q["R"] / t)
    return model("pyramid_skew_height", (("a", a), ("tangent", t)), q, (), q["H"])


def _vertices(name):
    parts = re.findall(r"[A-F](?:_1)?", name)
    if "".join(parts) != name or len(set(parts)) != len(parts):
        raise ContentPlanError("distinct canonical plane vertices are required")
    return parts


def _hex(groups, all_edges):
    a = positive(groups[0])
    h = a if all_edges else positive(groups[1])
    p1, p2, y, z, w = groups[1 if all_edges else 2 :]
    cycle = "ABCDEF"
    expected = (cycle[(cycle.index(y) + 1) % 6], cycle[(cycle.index(y) + 2) % 6])
    if {z, w} != set(expected) or set(_vertices(p1)) != {y, z + "_1", w + "_1"}:
        raise ContentPlanError(
            "the requested hexagonal prism section has another trapezoid"
        )
    if _vertices(p2)[2] != _vertices(p2)[1] + "_1":
        raise ContentPlanError(
            "the comparison plane must contain its stated vertical edge"
        )
    points = hex_points(a, sp.Integer(0))
    points.pop("S")
    points.update({n + "_1": v + sp.Matrix([0, 0, h]) for n, v in list(points.items())})

    def normal(name):
        p, q, r = (points[n] for n in _vertices(name))
        return (q - p).cross(r - p)

    if sp.simplify(normal(p1).dot(normal(p2))) != 0:
        raise ContentPlanError("the named prism planes are not perpendicular")
    q = {"a": a, "H": h, "leg": root(a * a + h * h), "offset": a / 2}
    return model(
        "hex_prism_distance",
        (("a", a), ("H", h)),
        q,
        (y, *expected, p2),
        root(h * h + 3 * a * a / 4),
    )


def _ratio(groups, angle):
    a, e, p, q = (positive(v) for v in groups[:4])
    fraction = sp.simplify(p / (p + q))
    dims = regular("triangle", {"a": a, "e": e})
    dims.update(p=p, q=q, fraction=fraction, AH=sp.sqrt(3) * a / 2)
    dims["AR"] = sp.simplify(fraction * dims["AH"])
    dims["distance"] = sp.simplify(dims["AR"] * dims["H"] / e)
    dims["foot"] = sp.simplify(a * a / (2 * e * e))
    dims["small_foot"] = sp.simplify(fraction * dims["foot"])
    if angle:
        cosine = sp.simplify(abs((e * e - a * a / 2) / (e * dims["l"])))
        dims["cosine"] = cosine
        return model(
            "ratio_plane_angle",
            (("a", a), ("e", e), ("p", p), ("q", q)),
            dims,
            (),
            sp.acos(cosine),
        )
    edge, r, s, vertex = groups[4:]
    if (edge, vertex) not in {("SB", "S"), ("AC", "A")} or sp.simplify(
        positive(r) / positive(s) - p / q
    ) != 0:
        raise ContentPlanError("the stated section ratio or reference vertex is false")
    return model(
        "ratio_plane_distance",
        (("a", a), ("e", e), ("p", p), ("q", q)),
        dims,
        (edge, vertex),
        dims["distance"],
    )


def read(raw):
    for pattern, solve in (
        (PROJECTION, lambda g: _projection(g, False)),
        (RENAMED, lambda g: _projection(g, True)),
        (TANGENT, _tangent),
    ):
        match = re.fullmatch(pattern, raw)
        if match:
            return solve(match.groups())
    for given, all_edges in HEX_GIVEN:
        match = re.fullmatch(HEX_HEADER + given + HEX_REQUEST, raw)
        if match:
            return _hex(match.groups(), all_edges)
    canonical = raw.replace(r"\colon", ":").replace(r"\alpha", "α")
    for suffix, angle in ((RATIO_DISTANCE, False), (RATIO_ANGLE, True)):
        match = re.fullmatch(RATIO_HEADER + suffix, canonical)
        if match:
            return _ratio(match.groups(), angle)
    return None
