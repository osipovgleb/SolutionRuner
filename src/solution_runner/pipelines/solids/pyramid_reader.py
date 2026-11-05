"""Match complete pyramid conditions before selecting an exact geometric calculation."""

import re

from ..core.errors import ContentPlanError
from ..probability.common import UnsupportedCondition
from .measurements import positive
from .prism_input import text
from .pyramid_model import (
    Pyramid,
    base_volume,
    face_angle,
    measured,
    perpendicular,
    perpendicular_face,
)
from .pyramid_named_reader import read as named
from .pyramid_ratios import cut, scaling, section
from .pyramid_sources import DATA, source_bytes

SPECS = (
    (
        "square_total_edge",
        r"Стороны основания правильной четырехугольной пирамиды равны\s+(.+?)\s*, боковые ребра равны\s+(.+?)\. Найдите площадь поверхности этой пирамиды\.",
        lambda g: measured("square_total_edge", "square", g, ("a", "e"), "S"),
    ),
    (
        "hex_lateral_edge",
        r"Стороны основания правильной шестиугольной пирамиды равны\s+(.+?)\s*, боковые ребра равны\s+(.+?)\. Найдите площадь боковой поверхности этой пирамиды\.",
        lambda g: measured("hex_lateral_edge", "hexagon", g, ("a", "e"), "L"),
    ),
    (
        "rectangle_height",
        r"Основанием пирамиды является прямоугольник со сторонами\s+(.+?)\s+и\s+(.+?)\. Ее объем равен\s+(.+?)\. Найдите высоту этой пирамиды\.",
        lambda g: base_volume("rectangle_height", g, "rectangle", "H"),
    ),
    (
        "triangle_volume",
        r"Найдите объем правильной треугольной пирамиды, стороны основания которой равны\s+(.+?)\s*, а высота равна\s+(.+?)\.",
        lambda g: base_volume("triangle_volume", g, "triangle", "V"),
    ),
    (
        "triangle_height",
        r"Найдите высоту правильной треугольной пирамиды, стороны основания которой равны\s+(.+?)\s*, а объем равен\s+(.+?)\.",
        lambda g: base_volume("triangle_height", g, "triangle", "H"),
    ),
    (
        "square_volume_height_edge",
        r"[ВB] правильной четырехугольной пирамиде высота равна\s+(.+?)\s*, боковое ребро равно\s+(.+?)\. Найдите ее объем\.",
        lambda g: measured("square_volume_height_edge", "square", g, ("H", "e"), "V"),
    ),
    (
        "perpendicular_face",
        r"Основанием пирамиды служит прямоугольник, одна боковая грань перпендикулярна плоскости основания, а три другие боковые грани наклонены к плоскости основания под углом\s+(.+?)°\. Высота пирамиды равна\s+(.+?)\. Найдите объем пирамиды\.",
        perpendicular_face,
    ),
    (
        "perpendicular",
        r"Боковые ребра треугольной пирамиды взаимно перпендикулярны, каждое из них равно\s+(.+?)\. Найдите объем пирамиды\.",
        perpendicular,
    ),
    (
        "hex_whole",
        r"Объем треугольной пирамиды SABC, являющейся частью правильной шестиугольной пирамиды SABCDEF, равен\s+(.+?)\. Найдите объем шестиугольной пирамиды\.",
        lambda g: cut("hex_whole", g),
    ),
    (
        "square_midpoint",
        r"Объем правильной четырехугольной пирамиды SABCD равен\s+(.+?)\. Точка E\s*[—–-]\s*середина ребра SB\. Найдите объем треугольной пирамиды EABC\.",
        lambda g: cut("square_midpoint", g),
    ),
    (
        "midline_cut",
        r"От треугольной пирамиды, объем которой равен\s+(.+?)\s*, отсечена треугольная пирамида плоскостью, проходящей через вершину пирамиды и среднюю линию основания\. Найдите объем отсеченной треугольной пирамиды\.",
        lambda g: cut("midline_cut", g),
    ),
    (
        "edge_cut",
        r"Объем треугольной пирамиды равен\s+(.+?)\. Плоскость проходит через сторону основания этой пирамиды и пересекает противоположное боковое ребро в точке, делящей его в отношении\s+(.+?)\s*:\s*(.+?)\s*, считая от вершины пирамиды\. Найдите больший из объемов пирамид, на которые плоскость разбивает исходную пирамиду\.",
        lambda g: cut("edge_cut", g),
    ),
    (
        "square_total_height",
        r"Найдите площадь поверхности правильной четырехугольной пирамиды, стороны основания которой равны\s+(.+?)\s+и высота равна\s+(.+?)\.",
        lambda g: measured("square_total_height", "square", g, ("a", "H"), "S"),
    ),
    (
        "square_lateral_height",
        r"Найдите площадь боковой поверхности правильной четырехугольной пирамиды, сторона основания которой равна\s+(.+?)\s+и высота равна\s+(.+?)\.",
        lambda g: measured("square_lateral_height", "square", g, ("a", "H"), "L"),
    ),
    (
        "tetra_section",
        r"Ребра тетраэдра равны\s+(.+?)\. Найдите площадь сечения, проходящего через середины четырех его ребер\.",
        lambda g: section("tetra_section", g),
    ),
    (
        "rectangle_volume",
        r"Найдите объем пирамиды, высота которой равна\s+(.+?)\s*, а основание\s*[—–-]\s*прямоугольник со сторонами\s+(.+?)\s+и\s+(.+?)\.",
        lambda g: base_volume("rectangle_volume", (g[1], g[2], g[0]), "rectangle", "V"),
    ),
    (
        "square_edge",
        r"[ВB] правильной четырехугольной пирамиде высота равна\s+(.+?)\s*, объем равен\s+(.+?)\. Найдите боковое ребро этой пирамиды\.",
        lambda g: measured("square_edge", "square", g, ("H", "V"), "e"),
    ),
    (
        "hex_volume_edge",
        r"Сторона основания правильной шестиугольной пирамиды равна\s+(.+?)\s*, боковое ребро равно\s+(.+?)\. Найдите объем пирамиды\.",
        lambda g: measured("hex_volume_edge", "hexagon", g, ("a", "e"), "V"),
    ),
    (
        "hex_edge",
        r"Объем правильной шестиугольной пирамиды (?:равен )?\s*(.+?)\. Сторона основания равна\s+(.+?)\. Найдите боковое ребро\.",
        lambda g: measured("hex_edge", "hexagon", g, ("V", "a"), "e"),
    ),
    (
        "hex_face_angle",
        r"Сторона основания правильной шестиугольной пирамиды равна\s+(.+?)\s*, а угол между боковой гранью и основанием равен\s+(.+?)°\. Найдите объем пирамиды\.",
        lambda g: face_angle("hexagon", g),
    ),
    (
        "box_tetrahedron",
        r"Объем параллелепипеда ABCDA_1B_1C_1D_1 равен\s+(.+?)\. Найдите объем треугольной пирамиды (?:B_1ABC|ABCB_1)\.",
        lambda g: cut("box_tetrahedron", g),
    ),
    (
        "cube_center",
        r"Объем куба равен\s+(.+?)\. Найдите объем четырехугольной пирамиды, основанием которой является грань куба, а вершиной\s*[—–-]\s*центр куба\.",
        lambda g: cut("cube_center", g),
    ),
    (
        "square_volume_side_edge",
        r"[ВB] правильной четырехугольной пирамиде SABCD с основанием ABCD боковое ребро S[A-D] равно\s+(.+?)\s*, сторона основания равна\s+(.+?)\. Найдите объем пирамиды\.",
        lambda g: measured("square_volume_side_edge", "square", g, ("e", "a"), "V"),
    ),
    (
        "square_section",
        r"[ВB] правильной четырехугольной пирамиде все ребра равны\s+(.+?)\. Найдите площадь сечения пирамиды плоскостью, проходящей через середины боковых ребер\.",
        lambda g: section("square_section", g),
    ),
)


def _floor(raw, source):
    match = re.fullmatch(
        r"Найдите объем пирамиды, изображенной на рисунке\. Ее основанием является многоугольник, соседние стороны которого перпендикулярны, а одно из боковых ребер перпендикулярно плоскости основания и равно\s+(.+?)\.",
        raw,
    )
    if not match:
        return None
    if source not in DATA["floor"]:
        raise ContentPlanError("the numeric orthogonal pyramid base needs review")
    source_bytes(source)
    record = DATA["floor"][source]
    x, y, u, v, h = tuple(positive(str(n)) for n in record["dimensions"])
    if positive(match[1]) != h or not (u < x and v < y):
        raise ContentPlanError(
            "the diagram dimensions differ from the pyramid condition"
        )
    area = x * y - u * v
    volume = area * h / 3
    return Pyramid(
        "floor",
        (h,),
        volume,
        "orthogonal",
        {"x": x, "y": y, "u": u, "v": v, "H": h, "B": area, "V": volume},
        (source,),
    )


def read(html, source=None):
    raw = text(html, source, labels="ABCDEFGHIJKLMNOPQRS")
    try:
        result = named(raw) or _floor(raw, source)
        if result:
            return result
        m = re.fullmatch(
            r"Во сколько раз увеличится (объем|площадь поверхности) (правильного тетраэдра|октаэдра|пирамиды), если все (?:его|ее) ребра увеличить в\s+(.+?)\s+раза?\?",
            raw,
        )
        if m:
            return scaling(m[2], "volume" if m[1] == "объем" else "area", m[3])
        m = re.fullmatch(
            r"Во сколько раз увеличится объем пирамиды, если ее высоту увеличить в\s+(.+?)\s+раза?\?",
            raw,
        )
        if m:
            return scaling("пирамиды", "volume", m[1], True)
        for kind, pattern, solve in SPECS:
            m = re.fullmatch(pattern, raw)
            if m:
                return solve(m.groups())
    except UnsupportedCondition as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError("one complete reviewed pyramid question is required")
