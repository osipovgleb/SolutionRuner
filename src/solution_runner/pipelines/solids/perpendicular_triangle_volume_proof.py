"""Retain the centroid or Menelaus section proof and the area-times-height volume."""

import sympy as sp

from ..probability.common import line
from .spatial_distance_proofs import parts
from .volume_section_format import bracket, value


def _centroid(m):
    u = m.names[0]
    return (
        "<p>Пусть плоскость сечения пересекает MD в точке E. Обозначим середину MB через F. Отрезок P F — средняя линия треугольника M"
        + u
        + "B, поэтому треугольник MPF — равносторонний, вдвое меньший исходного. Точка T — середина MF; прямая PT и прямая MD содержат медианы треугольника MPF. Поэтому E — точка пересечения этих медиан.</p>"
        + line(r"ME=\frac23\cdot\frac{MD}{2}=\frac{MD}{3}")
        + line(r"\frac{ME}{ED}=\frac{MD/3}{2MD/3}=\frac12")
    )


def _menelaus(m):
    q = m.q
    u, apex, _ = m.names
    ratio = sp.simplify(q["BT_fraction"] / q["MT_fraction"])
    return (
        "<p>Пусть плоскость "
        + apex
        + "PT пересекает MD в точке E, а прямая PT пересекает продолжение B"
        + u
        + " в точке Q. Применим теорему Менелая в треугольнике MB"
        + u
        + ":</p>"
        + line(r"\frac{" + u + r"P}{PM}\cdot\frac{MT}{TB}\cdot\frac{BQ}{Q" + u + "}=1")
        + line(r"\frac{BQ}{Q" + u + r"}=\frac{TB}{MT}=" + value(ratio))
        + "<p>D — середина B"
        + u
        + ", а Q лежит вне этого отрезка. Поэтому:</p>"
        + line(
            r"\frac{DQ}{Q"
            + u
            + r"}=\frac{BQ+Q"
            + u
            + "}{2Q"
            + u
            + r"}=\frac{"
            + value(ratio)
            + r"+1}{2}="
            + value(1 / q["cut_ratio"])
        )
        + "<p>Теперь применим теорему Менелая в треугольнике M"
        + u
        + "D:</p>"
        + line(r"\frac{" + u + r"P}{PM}\cdot\frac{ME}{ED}\cdot\frac{DQ}{Q" + u + "}=1")
        + line(r"\frac{ME}{ED}=\frac{Q" + u + "}{DQ}=" + value(q["cut_ratio"]))
    )


def _inequality(m):
    q = m.q
    bt = q["BT_fraction"] * q["a"]
    return (
        "<p>В треугольниках TBC и PCB углы TBC и PCB равны 60°. По теореме косинусов вычислим квадраты сравниваемых сторон:</p>"
        + line(r"CT^2=BT^2+BC^2-2\cdot BT\cdot BC\cdot\cos60^{\circ}")
        + line(
            r"CT^2="
            + bracket(bt)
            + "^2+"
            + bracket(q["a"])
            + r"^2-2\cdot "
            + bracket(bt)
            + r"\cdot "
            + bracket(q["a"])
            + r"\cdot\frac12="
            + value(q["CT_squared"])
        )
        + line(r"BP^2=CP^2+BC^2-2\cdot CP\cdot BC\cdot\cos60^{\circ}")
        + line(r"BP^2=\frac{3BC^2}{4}=" + value(q["BP_squared"]))
        + line(r"CT^2-BP^2=" + value(q["difference"]) + ">0")
        + "<p>Следовательно, CT &gt; BP.</p>"
    )


def _claim(m):
    if m.names[2] == "inequality":
        return _inequality(m)
    if m.q["MT_fraction"] == sp.Rational(1, 4):
        return _centroid(m)
    if m.q["MT_fraction"] == sp.Rational(1, 2):
        return "<p>P и T — середины двух сторон треугольника, поэтому PT — его средняя линия. Она пересекает медиану MD в её середине E. Следовательно, ME = ED, что и требовалось доказать.</p>"
    return _menelaus(m)


def _volume(m):
    q = m.q
    u, apex, _ = m.names
    altitude = apex + "D"
    base = "ABM" if u == "A" else "BCM"
    edge = "AB" if u == "A" else "BC"
    return (
        "<p>Проведём высоту "
        + altitude
        + " равностороннего треугольника ABC. Плоскости треугольников перпендикулярны и пересекаются по "
        + edge
        + ", поэтому эта высота перпендикулярна плоскости M"
        + u
        + "B. Она является высотой пирамиды, опущенной из вершины "
        + apex
        + " на плоскость основания MPT.</p>"
        + line(
            altitude
            + r"=\frac{"
            + edge
            + r"\sqrt3}{2}=\frac{"
            + bracket(q["a"])
            + r"\sqrt3}{2}="
            + value(q["height"])
        )
        + "<p>Треугольники MPT и M"
        + u
        + "B имеют общий угол M. Отношение их площадей равно произведению отношений прилегающих к этому углу сторон:</p>"
        + line(
            r"\frac{S_{MPT}}{S_{"
            + base
            + r"}}=\frac{MP}{M"
            + u
            + r"}\cdot\frac{MT}{MB}=\frac12\cdot "
            + bracket(q["MT_fraction"])
            + "="
            + value(q["area_fraction"])
        )
        + line(
            r"S_{MPT}="
            + bracket(q["area_fraction"])
            + r"\cdot\frac{"
            + bracket(q["a"])
            + r"^2\sqrt3}{4}="
            + value(q["section_area"])
        )
        + "<p>Найдём объём пирамиды:</p>"
        + line(r"V=\frac13 S_{MPT}\cdot " + altitude)
        + line(
            r"V=\frac13\cdot "
            + bracket(q["section_area"])
            + r"\cdot "
            + bracket(q["height"])
            + "="
            + value(m.answer)
        )
    )


def _alternative_inequality():
    return "<p><b>Другой способ доказательства пункта а).</b> Пусть K — середина MB. Треугольники BKC и CPB равны по двум сторонам и углу между ними: BK = CP, BC — общая сторона, углы KBC и PCB равны 60°. Значит, CK = BP. Медиана CK правильного треугольника BMC является высотой. Так как T не совпадает с K, отрезок CT — наклонная к BM и CT &gt; CK = BP.</p>"


def render(m, pictures):
    result = parts(pictures.get("image_1", "") + _claim(m), _volume(m))
    return result + (_alternative_inequality() if m.names[2] == "inequality" else "")
