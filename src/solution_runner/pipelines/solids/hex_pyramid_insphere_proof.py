"""Keep the similar-triangle inradius calculation and the total-surface alternative."""

import sympy as sp

from ..probability.common import line
from .spatial_distance_proofs import parts
from .volume_section_format import bracket, value


def _dimensions(m):
    q = m.q
    return (
        "<p>Пусть MH — высота правильной шестиугольной пирамиды MABCDEF. Из прямоугольного треугольника AMH:</p>"
        + line(r"MA=" + value(q["e"]) + r",\quad MH=" + value(q["H"]))
        + line(
            r"AH=\sqrt{MA^2-MH^2}=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["H"])
            + "^2}="
            + value(q["a"])
        )
        + "<p>Радиус описанной окружности правильного шестиугольника равен его стороне, поэтому AB = AH. Проведём высоту MN боковой грани AMB:</p>"
        + line(
            r"MN=\sqrt{MA^2-\left(\frac{AB}{2}\right)^2}=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["a"] / 2)
            + "^2}="
            + value(q["l"])
        )
    )


def _apothem(m):
    q = m.q
    return "<p>В равностороннем треугольнике AHB высота HN равна:</p>" + line(
        r"HN=\frac{AB\sqrt3}{2}=\frac{"
        + bracket(q["a"])
        + r"\sqrt3}{2}="
        + value(q["r"])
    )


def _claim(m):
    q = m.q
    if m.names[0] == "dihedral_angle":
        return (
            "<p>Двугранный угол при основании равен углу MNH. В прямоугольном треугольнике MNH:</p>"
            + line(
                r"\sin\angle MNH=\frac{MH}{MN}=\frac{"
                + value(q["H"])
                + "}{"
                + value(q["l"])
                + "}="
                + value(q["H"] / q["l"])
            )
            + line(r"\angle MNH=" + value(q["claimed_degrees"]) + r"^{\circ}")
        )
    return (
        _apothem(m)
        + "<p>Косинус двугранного угла при основании равен:</p>"
        + line(
            r"\cos\angle MNH=\frac{HN}{MN}=\frac{"
            + value(q["r"])
            + "}{"
            + value(q["l"])
            + "}="
            + value(q["r"] / q["l"])
        )
        + "<p>Проекции шести боковых граней на основание составляют его без перекрытий. Поэтому площадь основания равна площади боковой поверхности, умноженной на косинус этого угла:</p>"
        + line(r"S_{\mathrm{осн}}=S_{\mathrm{бок}}\cos\angle MNH")
        + line(
            r"\frac{S_{\mathrm{бок}}}{S_{\mathrm{осн}}}=\frac{MN}{HN}="
            + value(q["L"] / q["B"])
        )
    )


def _sphere(m):
    q = m.q
    ratio = sp.simplify(q["l"] / q["r"])
    return (
        (_apothem(m) if m.names[0] == "dihedral_angle" else "")
        + "<p>Центр O вписанной сферы лежит на высоте MH, а точка K её касания с гранью AMB — на MN. Обозначим радиус сферы через r. Прямоугольные треугольники MOK и MNH подобны, поэтому:</p>"
        + line(r"\frac{MO}{OK}=\frac{MN}{HN}")
        + line(r"(MH-r)HN=MN\cdot r")
        + line(r"r=\frac{MH\cdot HN}{MN+HN}=\frac{MH}{1+MN/HN}")
        + line(r"r=\frac{" + value(q["H"]) + "}{1+" + value(ratio) + "}")
        + "<p>Умножим числитель и знаменатель на сопряжённое выражение:</p>"
        + line(
            r"r=\frac{"
            + bracket(q["H"])
            + r"\left("
            + value(ratio)
            + r"-1\right)}{"
            + bracket(ratio)
            + "^2-1}="
            + value(q["sphere_radius"])
        )
        + "<p>Вычислим площадь сферы:</p>"
        + line(
            r"r^2="
            + bracket(q["sphere_radius"])
            + "^2="
            + value(sp.expand(q["sphere_radius"] ** 2))
        )
        + line(
            r"S=4\pi r^2=4\pi\cdot "
            + bracket(sp.expand(q["sphere_radius"] ** 2))
            + "="
            + value(m.answer)
        )
    )


def _alternative(m):
    q = m.q
    return (
        "<p><b>Другой способ нахождения радиуса.</b> Пирамида разбивается на пирамиды с вершиной O и основаниями на её гранях. Высота каждой из них равна r, поэтому V = rSполн/3. Найдём объём и площадь полной поверхности исходной пирамиды:</p>"
        + line(r"S_{\mathrm{осн}}=6\cdot\frac{AB^2\sqrt3}{4}=" + value(q["B"]))
        + line(
            r"V=\frac13 S_{\mathrm{осн}}\cdot MH=\frac13\cdot "
            + bracket(q["B"])
            + r"\cdot "
            + bracket(q["H"])
            + "="
            + value(q["V"])
        )
        + line(
            r"S_{\mathrm{полн}}=S_{\mathrm{осн}}+S_{\mathrm{бок}}="
            + value(q["B"])
            + "+"
            + value(q["L"])
            + "="
            + value(q["S"])
        )
        + line(
            r"r=\frac{3V}{S_{\mathrm{полн}}}=\frac{3\cdot "
            + bracket(q["V"])
            + "}{"
            + value(q["S"])
            + "}="
            + value(q["sphere_radius"])
        )
    )


def render(m, pictures):
    return parts(
        pictures.get("image_1", "") + _dimensions(m) + _claim(m), _sphere(m)
    ) + _alternative(m)
