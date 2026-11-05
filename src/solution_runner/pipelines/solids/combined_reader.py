"""Match complete reviewed combination questions, including reversed child questions."""

import re

from ..core.errors import ContentPlanError
from ..probability.common import UnsupportedCondition
from . import combined_model as model
from .prism_input import text

COMMON = r"Цилиндр и конус имеют общие основание и высоту\. "
EQUATOR = r"Конус вписан в шар\. Радиус основания конуса равен радиусу шара\. "
SPHERE_CONE = (
    r"Около конуса описана сфера \(сфера содержит окружность основания конуса и его вершину\)\. "
    r"Центр сферы (?:находится в центре|совпадает с центром) основания конуса\. "
)
PRISM_CYLINDER = (
    r"Правильная четырехугольная призма описана около цилиндра, радиус основания"
)
SPECS = (
    (
        "sphere_cylinder_surface",
        r"Шар вписан в цилиндр\. Площадь полной поверхности цилиндра равна (.+?)\. Найдите площадь поверхности шара\.",
        model.ratio,
    ),
    (
        "cylinder_sphere_surface",
        r"Шар вписан в цилиндр\. Площадь поверхности шара равна (.+?)\. Найдите площадь полной поверхности цилиндра\.",
        model.ratio,
    ),
    (
        "sphere_cylinder_volume",
        r"Цилиндр описан около шара\. Объем цилиндра равен (.+?)\. Найдите объем шара\.",
        model.ratio,
    ),
    (
        "sphere_cylinder_volume",
        r"Шар вписан в цилиндр объемом (.+?)\. Найдите объем шара\.",
        model.ratio,
    ),
    (
        "cylinder_sphere_volume",
        r"Цилиндр описан около шара\. Объем шара равен (.+?)\. Найдите объем цилиндра\.",
        model.ratio,
    ),
    (
        "cylinder_cone_volume",
        COMMON + r"Объем конуса равен (.+?)\. Найдите объем цилиндра\.",
        model.ratio,
    ),
    (
        "cone_cylinder_volume",
        COMMON + r"Найдите объем конуса, если объем цилиндра равен (.+?)\.",
        model.ratio,
    ),
    (
        "cone_cylinder_volume",
        COMMON + r"Объем цилиндра равен (.+?)\. Найдите объем конуса\.",
        model.ratio,
    ),
    (
        "cylinder_cone_volume",
        r"Конус и цилиндр имеют общее основание и общую высоту \(конус вписан в цилиндр\)\. Вычислите объем цилиндра, если объем конуса равен (.+?)\.",
        model.ratio,
    ),
    (
        "cone_sphere_volume",
        EQUATOR + r"Объем шара равен (.+?)\. Найдите объем конуса\.",
        model.ratio,
    ),
    (
        "sphere_cone_volume",
        EQUATOR + r"Объем конуса равен (.+?)\. Найдите объем шара\.",
        model.ratio,
    ),
    (
        "cone_cylinder_lateral",
        COMMON
        + r"Высота цилиндра равна радиусу основания\. Площадь боковой поверхности цилиндра равна (.+?)\. Найдите площадь боковой поверхности конуса\.",
        model.ratio,
    ),
    (
        "pyramid_outer_cone_volume",
        r"Объем конуса, вписанного в правильную четырехугольную пирамиду, равен (.+?)\. Найдите объем конуса, описанного около этой пирамиды\.",
        model.ratio,
    ),
    (
        "pyramid_inner_cone_volume",
        r"Объем конуса, описанного около правильной четырехугольной пирамиды, равен (.+?)\. Найдите объем конуса, вписанного в эту пирамиду\.",
        model.ratio,
    ),
    (
        "cube_around_sphere_volume",
        r"В куб вписан шар радиуса (.+?)\. Найдите объем куба\.",
        model.cube,
    ),
    (
        "cube_around_sphere_volume",
        r"Куб описан около сферы радиус(?:а|ом) (.+?)\. Найдите объем куба\.",
        model.cube,
    ),
    (
        "cube_around_sphere_surface",
        r"Прямоугольный параллелепипед описан около сферы радиус(?:а|ом) (.+?)\. Найдите (?:его площадь поверхности|площадь его поверхности)\.",
        model.cube,
    ),
    (
        "cube_insphere_radius",
        r"Объем куба, описанного около сферы, равен (.+?)\. Найдите радиус сферы\.",
        model.cube,
    ),
    (
        "cube_insphere_volume",
        r"В куб с ребром (.+?) вписан шар\. Найдите объем этого шара, деленный на \\pi\.",
        model.cube,
    ),
    (
        "cube_circumsphere_volume",
        r"Около куба с ребром (.+?) описан шар\. Найдите объем этого шара, деленный на \\pi\.",
        model.cube,
    ),
    (
        "cube_in_sphere_volume",
        r"Куб вписан в шар радиуса (.+?)\. Найдите объем куба\.",
        model.cube,
    ),
    (
        "cube_sphere_volume",
        r"Шар, объем которого равен (.+?), вписан в куб\. Найдите объем куба\.",
        model.cube,
    ),
    (
        "cone_sphere_radius",
        SPHERE_CONE + r"Образующая конуса равна (.+?)\. Найдите радиус сферы\.",
        model.cone_sphere,
    ),
    (
        "cone_sphere_slant",
        SPHERE_CONE + r"Радиус сферы равен (.+?)\. Найдите образующую конуса\.",
        model.cone_sphere,
    ),
)
PRISM_SPECS = (
    (
        "box_cylinder_volume",
        r"Прямоугольный параллелепипед описан около цилиндра, радиус основания и высота которого равны (.+?)\. Найдите объем параллелепипеда\.",
        True,
    ),
    (
        "box_cylinder_height",
        r"Прямоугольный параллелепипед описан около цилиндра, радиус основания которого равен (.+?)\. Объем параллелепипеда равен (.+?)\. Найдите высоту цилиндра\.",
        False,
    ),
    (
        "square_cylinder_lateral",
        PRISM_CYLINDER
        + r" и высота которого равны (.+?)\. Найдите площадь боковой поверхности призмы\.",
        True,
    ),
    (
        "square_cylinder_height",
        PRISM_CYLINDER
        + r" которого равен (.+?)\. Площадь боковой поверхности призмы равна (.+?)\. Найдите высоту цилиндра\.",
        False,
    ),
    (
        "triangle_around_cylinder_lateral",
        r"Найдите площадь боковой поверхности правильной треугольной призмы, описанной около цилиндра, радиус основания которого равен (.+?), а высота равна (.+?)\.",
        False,
    ),
    (
        "triangle_in_cylinder_lateral",
        r"Найдите площадь боковой поверхности правильной треугольной призмы, вписанной в цилиндр, радиус основания которого равен (.+?), а высота равна (.+?)\.",
        False,
    ),
    (
        "hexagon_cylinder_lateral",
        r"Найдите площадь боковой поверхности правильной шестиугольной призмы, описанной около цилиндра, радиус основания которого равен (.+?), а высота равна (.+?)\.",
        False,
    ),
)


def _special(raw):
    m = re.fullmatch(
        r"Прямоугольный параллелепипед описан около единичной сферы\. Найдите его площадь поверхности\.",
        raw,
    )
    if m:
        return model.cube("cube_around_sphere_surface", "1")
    m = re.fullmatch(
        r"В основании прямой призмы лежит (?:прямоугольный треугольник с катетами (.+?) и (.+?)|квадрат со стороной (.+?))\. Боковые ребра равны \\frac\{(.+?)\}\{\\pi\}\.\.? Найдите объем цилиндра, описанного около этой призмы\.",
        raw,
    )
    if m:
        a, b, side, h = m.groups()
        return model.cylinder_around_prism(
            "cylinder_around_triangle" if a is not None else "cylinder_around_square",
            (a, b, h) if a is not None else (side, h),
        )
    m = re.fullmatch(
        r"Конус описан около правильной четырехугольной пирамиды со стороной основания (.+?) и высотой (.+?)\. Найдите его объем, деленный на \\pi\.",
        raw,
    )
    if m:
        return model.pyramid_cone(m.groups())
    m = re.fullmatch(
        r"Во сколько раз объем конуса, описанного около правильной четырехугольной пирамиды, больше объема конуса, вписанного в эту пирамиду\?",
        raw,
    )
    if m:
        return model.ratio("pyramid_cones_ratio")
    return _parts(raw)


def _parts(raw):
    m = re.fullmatch(
        r"Из единичного куба вырезана правильная четырехугольная призма со стороной основания (.+?) и боковым ребром (.+?)\. Найдите площадь поверхности оставшейся части куба\.?",
        raw,
    )
    if m:
        return model.cube_hole(m.groups())
    m = re.fullmatch(
        r"Вершина A куба ABCDA_1B_1C_1D_1 с ребром (.+?) является центром сферы, проходящей через точку A_1\. Найдите площадь S части сферы, содержащейся внутри куба\. В ответе запишите величину S\\div \\pi\.",
        raw,
    )
    if m:
        return model.sphere_part("sphere_vertex_part", m.groups())
    m = re.fullmatch(
        r"Середина ребра куба со стороной (.+?) является центром шара радиуса (.+?)\. Найдите площадь S части поверхности шара, лежащей внутри куба\. В ответе запишите S\\div \\pi\.",
        raw,
    )
    if m:
        return model.sphere_part("sphere_edge_part", m.groups())
    m = re.fullmatch(
        r"(Объем тетраэдра равен|Площадь поверхности тетраэдра равна) (.+?)\.? Найдите (объем|площадь поверхности) многогранника, вершинами которого являются середины (?:ребер|сторон) данного тетраэдра\.",
        raw,
    )
    if m:
        volume = m[1].startswith("Объем")
        if volume != (m[3] == "объем"):
            raise ContentPlanError(
                "the tetrahedron measure differs from the requested measure"
            )
        return model.ratio(
            "tetra_midpoint_volume" if volume else "tetra_midpoint_surface", m[2]
        )
    return None


def read(html, source=None):
    raw = text(html, source, labels="ABCDS").replace("π", r"\pi")
    raw = re.sub(r"\bB (?=куб|основании|ответе)", "В ", raw)
    try:
        for kind, pattern, solve in SPECS:
            m = re.fullmatch(pattern, raw)
            if m:
                return solve(kind, m[1])
        for kind, pattern, repeat in PRISM_SPECS:
            m = re.fullmatch(pattern, raw)
            if m:
                return model.prism(kind, m.groups() * 2 if repeat else m.groups())
        answer = _special(raw)
        if answer is not None:
            return answer
    except UnsupportedCondition as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError("one complete reviewed combination question is required")
