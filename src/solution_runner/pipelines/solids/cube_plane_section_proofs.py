"""Keep similarity and two-volume calculation before the coordinate alternative."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts
from .spatial_metric_proofs import picture


def _base_midpoint(m):
    q = m.q
    return (
        "<p>Пусть AP и BC пересекаются в точке R. Тогда M — точка пересечения QR и CC₁. Треугольники ARB и PRC подобны:</p>"
        + line("PC=CD-DP=" + value(q["a"]) + "-" + value(q["p"]) + "=" + value(q["PC"]))
        + line(
            r"\frac{RC}{RB}=\frac{PC}{AB}=\frac{"
            + value(q["PC"])
            + "}{"
            + value(q["a"])
            + "}"
        )
        + "<p>Учитывая RB = RC + BC, найдём RC:</p>"
        + line(
            r"RC=\frac{PC\cdot BC}{AB-PC}=\frac{"
            + bracket(q["PC"])
            + r"\cdot "
            + bracket(q["a"])
            + "}{"
            + value(q["a"])
            + "-"
            + value(q["PC"])
            + "}="
            + value(q["RC"])
        )
        + line(
            "BQ=BB_1-B_1Q=" + value(q["a"]) + "-" + value(q["b"]) + "=" + value(q["BQ"])
        )
        + "<p>Из подобия треугольников QRB и MRC:</p>"
        + line(r"\frac{MC}{QB}=\frac{RC}{RB}=\frac{PC}{AB}")
        + line(
            r"MC=\frac{"
            + value(q["PC"])
            + "}{"
            + value(q["a"])
            + r"}\cdot "
            + bracket(q["BQ"])
            + "="
            + value(q["CM"])
        )
        + line(r"MC=\frac{CC_1}{2}")
        + "<p>Следовательно, M — середина CC₁.</p>"
    )


def _vertical_midpoint(m, pictures):
    q = m.q
    return (
        "<p>Пусть K и N — центры граней ABCD и A₁B₁C₁D₁, O — пересечение PQ и KN. Прямая KN лежит в обеих диагональных плоскостях ACC₁A₁ и BDD₁B₁, поэтому O лежит также на A₁M.</p>"
        + pictures.get("image_2", "")
        + "<p>В прямоугольнике DBB₁D₁ точка O лежит над серединой DB. Отсюда её расстояние до верхнего основания равно полусумме расстояний от P и Q до него:</p>"
        + line(
            "D_1P=DD_1-DP="
            + value(q["a"])
            + "-"
            + value(q["p"])
            + "="
            + value(q["a"] - q["p"])
        )
        + line(
            r"ON=\frac{D_1P+B_1Q}{2}=\frac{"
            + value(q["a"] - q["p"])
            + "+"
            + value(q["b"])
            + "}{2}="
            + value(q["C1M"] / 2)
        )
        + "<p>В треугольнике A₁C₁M точка N — середина A₁C₁, а NO ∥ C₁M. Значит, NO — средняя линия:</p>"
        + line("C_1M=2ON=2\\cdot " + bracket(q["C1M"] / 2) + "=" + value(q["C1M"]))
        + line(r"C_1M=\frac{CC_1}{2}")
        + "<p>Следовательно, M — середина CC₁.</p>"
    )


def _volume(m):
    q = m.q
    if m.mode == "cube_base_plane_distance":
        return (
            "<p>Искомое расстояние h — высота пирамиды CPRM к грани RPM: эта грань лежит в плоскости APQ. Сначала выразим её объём через основание MPC. Треугольник MPC прямоугольный, а RC перпендикулярна его плоскости:</p>"
            + line(r"V=\frac{1}{3}RC\cdot S_{MPC}=\frac{RC\cdot PC\cdot CM}{6}")
            + line(
                r"V=\frac{"
                + bracket(q["RC"])
                + r"\cdot "
                + bracket(q["PC"])
                + r"\cdot "
                + bracket(q["CM"])
                + "}{6}="
                + value(q["V"])
            )
        )
    return (
        "<p>Искомое расстояние h — высота пирамиды C₁PQM к грани PQM, лежащей в плоскости A₁PQ. Возьмём основанием треугольник QMC₁. Его площадь равна половине произведения C₁M на BC, а расстояние от P до его плоскости равно C₁D₁:</p>"
        + line(r"V=\frac{1}{3}C_1D_1\cdot S_{QMC_1}=\frac{C_1D_1\cdot BC\cdot C_1M}{6}")
        + line(
            r"V=\frac{"
            + bracket(q["a"])
            + r"\cdot "
            + bracket(q["a"])
            + r"\cdot "
            + bracket(q["C1M"])
            + "}{6}="
            + value(q["V"])
        )
    )


def _edges(m):
    q = m.q
    if m.mode == "cube_base_plane_distance":
        return (
            "<p>По теореме Пифагора в прямоугольных треугольниках найдём стороны RPM:</p>"
            + line(
                r"RP=\sqrt{RC^2+PC^2}=\sqrt{"
                + bracket(q["RC"])
                + "^2+"
                + bracket(q["PC"])
                + "^2}="
                + value(q["RP"])
            )
            + line(
                r"RM=\sqrt{RC^2+CM^2}=\sqrt{"
                + bracket(q["RC"])
                + "^2+"
                + bracket(q["CM"])
                + "^2}="
                + value(q["RM"])
            )
            + line(
                r"MP=\sqrt{PC^2+CM^2}=\sqrt{"
                + bracket(q["PC"])
                + "^2+"
                + bracket(q["CM"])
                + "^2}="
                + value(q["MP"])
            )
        )
    return (
        "<p>Найдём стороны PQM по теореме Пифагора. Противоположные грани куба параллельны, поэтому их пересечения с секущей плоскостью параллельны. Значит, сечение A₁PMQ — параллелограмм, откуда PM = A₁Q и MQ = A₁P:</p>"
        + line(
            r"PM=\sqrt{A_1B_1^2+B_1Q^2}=\sqrt{"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["b"])
            + "^2}="
            + value(q["PM"])
        )
        + line(
            r"MQ=\sqrt{A_1D_1^2+D_1P^2}=\sqrt{"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["a"] - q["p"])
            + "^2}="
            + value(q["MQ"])
        )
        + line(r"PQ=\sqrt{B_1D_1^2+(B_1Q-D_1P)^2}")
        + line(
            r"PQ=\sqrt{2\cdot "
            + bracket(q["a"])
            + "^2+("
            + value(q["b"])
            + "-"
            + value(q["a"] - q["p"])
            + ")^2}="
            + value(q["PQ"])
        )
    )


def _area(m):
    q = m.q
    vertical = m.mode == "cube_vertical_plane_distance"
    first, second, third = ("PM", "MQ", "PQ") if vertical else ("RM", "RP", "MP")
    angle = "PMQ" if vertical else "MRP"
    face = "PQM" if vertical else "RPM"
    return (
        "<p>Применим теорему косинусов, а затем основное тригонометрическое тождество:</p>"
        + line(
            r"\cos\angle "
            + angle
            + r"=\frac{"
            + first
            + "^2+"
            + second
            + "^2-"
            + third
            + "^2}{2"
            + first
            + r"\cdot "
            + second
            + "}"
        )
        + line(
            r"\cos\angle "
            + angle
            + r"=\frac{"
            + bracket(q[first])
            + "^2+"
            + bracket(q[second])
            + "^2-"
            + bracket(q[third])
            + r"^2}{2\cdot "
            + bracket(q[first])
            + r"\cdot "
            + bracket(q[second])
            + "}="
            + value(q["cosine"])
        )
        + line(
            r"\sin\angle "
            + angle
            + r"=\sqrt{1-\cos^2\angle "
            + angle
            + r"}=\sqrt{1-"
            + bracket(q["cosine"])
            + "^2}="
            + value(q["sine"])
        )
        + "<p>Найдём площадь грани и выразим объём через неё:</p>"
        + line(
            "S_{"
            + face
            + r"}=\frac{1}{2}"
            + first
            + r"\cdot "
            + second
            + r"\cdot\sin\angle "
            + angle
        )
        + line(
            "S_{"
            + face
            + r"}=\frac{1}{2}\cdot "
            + bracket(q[first])
            + r"\cdot "
            + bracket(q[second])
            + r"\cdot "
            + bracket(q["sine"])
            + "="
            + value(q["face_area"])
        )
        + line(r"V=\frac{1}{3}hS_{" + face + "}")
        + line(
            r"h=\frac{3V}{S_{"
            + face
            + r"}}=\frac{3\cdot "
            + bracket(q["V"])
            + "}{"
            + value(q["face_area"])
            + "}="
            + value(m.answer)
        )
    )


def coordinates(m, pictures):
    q = m.q
    vertical = m.mode == "cube_vertical_plane_distance"
    x, y, z = sp.symbols("x y z")
    equation = sp.latex(q["nx"] * x + y + q["nz"] * z + q["constant"]) + "=0"
    first = (
        "<p>Поместим начало координат в B, оси направим по BA, BC и BB₁. Обозначим ребро куба через a, длины DP и B₁Q — через p и b. Тогда "
        + (
            "A₁(a; 0; a), P(a; a; p), Q(0; 0; a−b)."
            if vertical
            else "A(a; 0; 0), P(a−p; a; 0), Q(0; 0; a−b)."
        )
        + " Подставляя координаты этих трёх точек в общее уравнение плоскости, получаем:</p>"
        + line(equation)
        + "<p>Середина CC₁ имеет координаты (0; a; a/2). Проверим, что она лежит в найденной плоскости:</p>"
        + line(
            value(q["nx"])
            + r"\cdot 0+"
            + value(q["a"])
            + "+"
            + bracket(q["nz"])
            + r"\cdot "
            + bracket(q["a"] / 2)
            + "+"
            + bracket(q["constant"])
            + "=0"
        )
        + "<p>Следовательно, эта середина совпадает с M: прямая CC₁ пересекает плоскость в единственной точке.</p>"
    )
    if not vertical:
        first = pictures.get("image_2", "") + first
    target = "C₁(0; a; a)" if vertical else "C(0; a; 0)"
    z0 = q["a"] if vertical else sp.Integer(0)
    numerator = abs(q["a"] + q["nz"] * z0 + q["constant"])
    denominator = sp.sqrt(q["nx"] ** 2 + 1 + q["nz"] ** 2)
    second = (
        "<p>Воспользуемся формулой расстояния от точки до плоскости. Подставим координаты "
        + target
        + ":</p>"
        + line(
            r"h=\frac{\left|"
            + value(q["a"])
            + "+"
            + bracket(q["nz"])
            + r"\cdot "
            + bracket(z0)
            + "+"
            + bracket(q["constant"])
            + r"\right|}{\sqrt{"
            + bracket(q["nx"])
            + "^2+1+"
            + bracket(q["nz"])
            + "^2}}"
        )
        + line(
            r"h=\frac{"
            + value(numerator)
            + "}{"
            + value(denominator)
            + "}="
            + value(m.answer)
        )
    )
    return parts(first, second)


def render(m, pictures):
    first = (
        _vertical_midpoint(m, pictures)
        if m.mode == "cube_vertical_plane_distance"
        else _base_midpoint(m)
    )
    return (
        picture(pictures)
        + parts(first, _volume(m) + _edges(m) + _area(m))
        + "<p><b>Решение векторно-координатным методом.</b></p>"
        + coordinates(m, pictures)
    )
