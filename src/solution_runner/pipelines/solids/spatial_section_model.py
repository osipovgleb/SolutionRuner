"""Complete parallel-section constructions and the golden-angle bisector proof."""

import re

import sympy as sp

from ..core.errors import ContentPlanError
from .measurements import positive
from .pyramid_model import regular, root
from .spatial_metric_model import model

MODES = {
    "pyramid_parallel_section_height",
    "triangle_bisector_section_edge",
    "triangle_bisector_section_area",
    "pyramid_parallel_section_area",
    "pyramid_parallel_section_angle",
}
PARALLEL = (
    r"[ВB] основании пирамиды SABCD лежит прямоугольник ABCD со стороной AB\s*=\s*(.+?) и диагональю BD\s*=\s*(.+?)\. "
    r"Все боковые ребра пирамиды равны (.+?)\. На диагонали BD основания ABCD отмечена точка E, а на ребре AS [—–-] точка F так, что SF\s*=\s*BE\s*=\s*(.+?)\. "
    r"Докажите, что плоскость CEF параллельна ребру SB\. Плоскость CEF пересекает ребро SD в точке Q\. Найдите расстояние от точки Q до плоскости ABC\."
)
BISECTOR = (
    r"[ВB] правильной треугольной пирамиде SABC с основанием ABC угол ASB равен (.+?)°\. На ребре SC взята точка M так, что AM [—–-] биссектриса угла SAC\. "
    r"Докажите, что AM\s*=\s*AB\. "
)
EDGE = r"Площадь сечения пирамиды, проходящего через точки A, M и B, равна (.+?)\. Найдите сторону основания\."
AREA = r"Сторона основания (.+?)\. Найдите площадь сечения пирамиды, проходящего через точки A, M и B\."
TRAPEZOID = (
    r"[ВB] правильной четырехугольной пирамиде PABCD, все ребра которой равны (.+?), точка K [―—–-] середина бокового ребра AP\. "
    r"Постройте сечение пирамиды плоскостью, проходящей через точку K и параллельной (прямым PB и BC|плоскости BCP)\. "
    r"Найдите (площадь сечения|угол между плоскостью сечения и плоскостью основания пирамиды)\."
)


def _parallel(groups):
    a, d, e, t = map(positive, groups)
    if not (a < d and t < min(d, e)) or sp.simplify(e - (d - t)) != 0:
        raise ContentPlanError(
            "the edge positions do not give a section parallel to SB"
        )
    h = root(e * e - d * d / 4)
    q = {
        "a": a,
        "d": d,
        "e": e,
        "t": t,
        "H": h,
        "DE": d - t,
        "BM": a * t / (d - t),
        "AM": a - a * t / (d - t),
        "AF": e - t,
    }
    return model(
        "pyramid_parallel_section_height",
        tuple(zip(("a", "d", "e", "t"), (a, d, e, t), strict=True)),
        q,
        (),
        (d - t) * h / d,
    )


def _bisector(groups, area):
    angle, given = map(positive, groups)
    if angle != 36:
        raise ContentPlanError(
            "the stated bisector equality requires the 36-degree vertex angle"
        )
    a = given if area else root(4 * given / sp.sqrt(3))
    q = regular("triangle", {"a": a, "e": (1 + sp.sqrt(5)) * a / 2})
    q.update(
        section_area=sp.sqrt(3) * a * a / 4,
        vertex_angle=angle,
        base_angle=(180 - angle) / 2,
    )
    return model(
        "triangle_bisector_section_area" if area else "triangle_bisector_section_edge",
        (("a" if area else "section_area", given),),
        q,
        (),
        q["section_area"] if area else a,
    )


def _trapezoid(groups):
    a = positive(groups[0])
    angle = groups[2].startswith("угол")
    q = regular("square", {"a": a, "e": a})
    q.update(
        offset=a / 4,
        section_height=sp.sqrt(3) * a / 4,
        section_area=3 * sp.sqrt(3) * a * a / 16,
    )
    return model(
        "pyramid_parallel_section_angle" if angle else "pyramid_parallel_section_area",
        (("a", a),),
        q,
        (),
        sp.acos(1 / sp.sqrt(3)) if angle else q["section_area"],
    )


def read(raw):
    for pattern, solve in (
        (PARALLEL, _parallel),
        (BISECTOR + EDGE, lambda g: _bisector(g, False)),
        (BISECTOR + AREA, lambda g: _bisector(g, True)),
        (TRAPEZOID, _trapezoid),
    ):
        match = re.fullmatch(pattern, raw)
        if match:
            return solve(match.groups())
    return None
