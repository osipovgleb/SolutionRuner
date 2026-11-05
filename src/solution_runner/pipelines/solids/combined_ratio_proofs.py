"""Explain the parents' surface, volume, diameter and midpoint ratios."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value

SC = r"S_{\mathrm{цил}}"
SS = r"S_{\mathrm{ш}}"
VC = r"V_{\mathrm{цил}}"
VS = r"V_{\mathrm{ш}}"
VK = r"V_{\mathrm{кон}}"


def substitution(symbol, factor, given, answer):
    return line(
        symbol + "=" + bracket(factor) + r"\cdot" + bracket(given) + "=" + value(answer)
    )


def sphere_cylinder_surface(m):
    inverse = m.kind == "cylinder_sphere_surface"
    target, given = (SC, SS) if inverse else (SS, SC)
    rows = (
        "<p>Радиусы шара и основания цилиндра равны. Высота цилиндра равна диаметру шара:</p>"
        + line("h=2r")
        + line(SC + r"=2\pi r^2+2\pi rh")
        + line(SC + r"=2\pi r^2+4\pi r^2=6\pi r^2")
        + "<p>Площадь поверхности шара равна четырём площадям его большого круга. Сравним площади поверхностей:</p>"
        + line(SS + r"=4\pi r^2")
        + line(target + "=" + value(m.q["factor"]) + given)
    )
    return rows + substitution(target, m.q["factor"], m.given[0], m.answer)


def sphere_cylinder_volume(m):
    inverse = m.kind == "cylinder_sphere_volume"
    rows = (
        "<p>Радиус основания цилиндра равен радиусу шара, а высота — его диаметру. Запишем объём цилиндра:</p>"
        + line("h=2R")
        + line(VC + r"=\pi R^2h=2\pi R^3")
    )
    if inverse:
        return (
            rows
            + "<p>Выразим объём цилиндра через объём вписанного шара:</p>"
            + line(VS + r"=\frac{4}{3}\pi R^3")
            + line(VC + r"=\frac{3}{2}" + VS)
            + substitution(VC, m.q["factor"], m.given[0], m.answer)
        )
    return (
        rows
        + line(VC + "=" + value(m.given[0]))
        + "<p>Выразим куб радиуса и подставим в формулу объёма шара:</p>"
        + line(r"R^3=\frac{" + value(m.given[0]) + r"}{2\pi}")
        + line(VS + r"=\frac{4}{3}\pi R^3")
        + line(
            VS
            + r"=\frac{4}{3}\pi\cdot\frac{"
            + value(m.given[0])
            + r"}{2\pi}="
            + value(m.answer)
        )
    )


def cone_cylinder(m, cylinder_first=False):
    cylinder = line(VC + "=Bh")
    cone = line(VK + r"=\frac{1}{3}Bh")
    target, given = (VC, VK) if m.kind == "cylinder_cone_volume" else (VK, VC)
    return (
        "<p>Обозначим общую площадь основания через B, а общую высоту — через h. Объём цилиндра равен произведению площади основания на высоту, объём конуса — трети этого произведения:</p>"
        + (cylinder + cone if cylinder_first else cone + cylinder)
        + line(VC + "=3" + VK)
        + "<p>Используем соотношение объёмов для искомого тела:</p>"
        + line(target + "=" + value(m.q["factor"]) + given)
        + substitution(target, m.q["factor"], m.given[0], m.answer)
    )


def cone_sphere(m):
    inverse = m.kind == "sphere_cone_volume"
    target, given = (VS, VK) if inverse else (VK, VS)
    return (
        "<p>Радиус основания конуса равен радиусу шара R. Основание конуса проходит через центр шара, поэтому его высота также равна R:</p>"
        + line("h=R")
        + (
            line(VK + r"=\frac{1}{3}\pi R^2h")
            if inverse
            else line(VS + r"=\frac{4}{3}\pi R^3")
        )
        + line(VK + r"=\frac{1}{3}\pi R^3")
        + (line(VS + r"=\frac{4}{3}\pi R^3") if inverse else "")
        + "<p>Объём шара в четыре раза больше объёма этого конуса. Подставим известный объём:</p>"
        + line(target + "=" + value(m.q["factor"]) + given)
        + substitution(target, m.q["factor"], m.given[0], m.answer)
    )


def cone_cylinder_lateral(m):
    return (
        "<p>Конус и цилиндр имеют общую высоту и равные радиусы основания. По условию высота равна радиусу:</p>"
        + line("h=r")
        + line(SC + r"=2\pi rh=2\pi r^2")
        + line(r"\pi r^2=\frac{" + value(m.given[0]) + "}{2}=" + value(m.given[0] / 2))
        + "<p>Найдём образующую конуса по теореме Пифагора, затем площадь его боковой поверхности:</p>"
        + line(r"l^2=h^2+r^2=2r^2")
        + line(r"l=r\sqrt{2}")
        + line(r"S_{\mathrm{кон}}=\pi rl=\pi r^2\sqrt{2}")
        + line(
            r"S_{\mathrm{кон}}="
            + bracket(m.given[0] / 2)
            + r"\cdot\sqrt{2}="
            + value(m.answer)
        )
    )


def pyramid_cones(m):
    rows = (
        "<p>Высоты двух конусов равны высоте пирамиды. Диаметр вписанного конуса равен стороне a квадрата, а диаметр описанного — его диагонали:</p>"
        + line("d_1=a")
        + line(r"d_2=a\sqrt{2}")
        + "<p>Объёмы конусов с общей высотой относятся как площади оснований, то есть как квадраты диаметров:</p>"
        + line(r"\frac{V_2}{V_1}=\frac{d_2^2}{d_1^2}")
        + line(r"\frac{V_2}{V_1}=\frac{2a^2}{a^2}=2")
    )
    if m.kind == "pyramid_cones_ratio":
        return rows + line("V_2=2V_1")
    target, given = (
        ("V_2", "V_1") if m.kind == "pyramid_outer_cone_volume" else ("V_1", "V_2")
    )
    return (
        rows
        + line(target + "=" + value(m.q["factor"]) + given)
        + substitution(target, m.q["factor"], m.given[0], m.answer)
    )


def tetra_midpoints(m):
    if m.kind == "tetra_midpoint_volume":
        return (
            "<p>От исходного тетраэдра отсечены четыре тетраэдра. Каждый подобен исходному с коэффициентом 1/2:</p>"
            + line(r"k=\frac{1}{2}")
            + line(r"V_1=k^3V_0=\frac{1}{8}V_0")
            + "<p>Вычтем их объёмы из объёма исходного тетраэдра:</p>"
            + line("V=V_0-4V_1")
            + line(r"V=V_0-\frac{1}{2}V_0=\frac{1}{2}V_0")
            + substitution("V", m.q["factor"], m.given[0], m.answer)
        )
    return (
        "<p>На каждой грани исходного тетраэдра средние линии образуют треугольник, площадь которого равна четверти площади этой грани. Сумма площадей четырёх таких треугольников:</p>"
        + line(r"k=\frac{1}{2}")
        + line(r"k^2=\frac{1}{4}")
        + line(r"S_1=\frac{1}{4}S_0")
        + "<p>Ещё четыре грани сечения у вершин попарно равны этим треугольникам. Поэтому искомая площадь равна половине исходной:</p>"
        + line("S=2S_1")
        + line(r"S=\frac{1}{2}S_0")
        + substitution("S", m.q["factor"], m.given[0], m.answer)
        + "<p>Примечание. Равны треугольники в каждой из четырёх пар. Треугольники из разных пар могут быть не равны.</p>"
    )
