"""Use a rectangular trapezoid as pyramid base, then retain the prism-half alternative."""

from ..probability.common import line
from .spatial_distance_proofs import parts
from .volume_section_format import bracket, value


def _equal_volumes():
    return "<p>Оба пятигранника — четырёхугольные пирамиды: ABCA₁D имеет вершину C и основание ABDA₁, а A₁B₁C₁CD — вершину A₁ и основание DB₁C₁C. Основания — равные прямоугольные трапеции: их параллельные стороны равны боковому ребру призмы и его половине, а расстояния между ними равны стороне основания призмы. Высоты пирамид равны высотам равных равносторонних треугольников ABC и A₁B₁C₁. Следовательно, объёмы пирамид равны.</p>"


def _distance():
    return (
        "<p>Пусть CM — высота треугольника ABC. Она перпендикулярна AB и параллельному боковому ребру AA₁ направлению, поэтому CM ⟂ (ABB₁). Прямая A₁D лежит в этой плоскости, а CC₁ параллельна ей.</p>"
        "<p>Через M проведём прямую, параллельную CC₁; она пересекает A₁D в точке K. Пусть L — точка CC₁ на той же высоте, что и K. Тогда KL ∥ CM и KL = CM. Отрезок KL перпендикулярен плоскости ABB₁, а также прямой CC₁, поэтому это общий перпендикуляр A₁D и CC₁.</p>"
        "<p>Таким образом, расстояние между A₁D и CC₁ равно CM. Расстояние от A до плоскости BCC₁ равно высоте треугольника ABC, проведённой из A. У равностороннего треугольника высоты равны, что и требовалось доказать.</p>"
    )


def _pyramid(m):
    q = m.q
    upper = m.names[0] == "upper"
    altitude = "A_1M" if upper else "CM"
    face = "DB_1C_1C" if upper else "ABDA_1"
    parallel = "CC_1+B_1D" if upper else "AA_1+BD"
    side = "B_1C_1" if upper else "AB"
    description = (
        "<p>Пятигранник A₁B₁C₁CD — пирамида с вершиной A₁ и основанием DB₁C₁C. Проведём высоту A₁M равностороннего треугольника A₁B₁C₁. Она перпендикулярна B₁C₁ и CC₁, поэтому перпендикулярна плоскости основания пирамиды BCC₁.</p>"
        if upper
        else "<p>Пятигранник ABCA₁D — пирамида с вершиной C и основанием ABDA₁. Высота CM равностороннего треугольника ABC перпендикулярна AB и AA₁, поэтому является высотой этой пирамиды.</p>"
    )
    return (
        description
        + line(
            altitude
            + r"=\frac{"
            + side
            + r"\sqrt3}{2}=\frac{"
            + bracket(q["a"])
            + r"\sqrt3}{2}="
            + value(q["base_altitude"])
        )
        + "<p>Площадь прямоугольной трапеции в основании равна:</p>"
        + line(r"S_{" + face + r"}=\frac{" + parallel + r"}{2}\cdot " + side)
        + line(
            r"S_{"
            + face
            + r"}=\frac{"
            + value(q["H"])
            + "+"
            + value(q["half_height"])
            + r"}{2}\cdot "
            + bracket(q["a"])
            + "="
            + value(q["trapezoid_area"])
        )
        + "<p>По формуле объёма пирамиды:</p>"
        + line(r"V=\frac13 S_{" + face + r"}\cdot " + altitude)
        + line(
            r"V=\frac13\cdot "
            + bracket(q["trapezoid_area"])
            + r"\cdot "
            + bracket(q["base_altitude"])
            + "="
            + value(m.answer)
        )
    )


def _alternative(m):
    q = m.q
    return (
        "<p><b>Другой способ вычисления объёма.</b> Плоскость CA₁D делит призму на два пятигранника равного объёма: их равенство следует из равенства оснований-трапеций и высот, рассмотренных выше. Поэтому достаточно найти половину объёма призмы:</p>"
        + line(r"V=\frac12 V_{\mathrm{призмы}}=\frac12 S_{ABC}\cdot AA_1")
        + line(
            r"V=\frac12\cdot\frac{"
            + bracket(q["a"])
            + r"^2\sqrt3}{4}\cdot "
            + bracket(q["H"])
            + "="
            + value(m.answer)
        )
    )


def render(m, pictures):
    claim = _distance() if m.names[1] == "distance" else _equal_volumes()
    if m.names[1] == "distance":
        alternative_claim = _equal_volumes()
    else:
        alternative_claim = ""
    return parts(
        pictures.get("image_1", "") + claim,
        _pyramid(m) + alternative_claim + _alternative(m),
    )
