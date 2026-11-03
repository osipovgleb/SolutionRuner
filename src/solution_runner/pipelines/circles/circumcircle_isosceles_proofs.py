"""Keep Heron, altitude/sine, center-distance and double-angle cosine methods."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from ..triangles.right.altitude_methods import solution_section
from .circumcircle_isosceles_model import kind


def _height(m):
    a, b = m.given
    h = sp.sqrt(a * a - b * b / 4)
    return line(
        r"CH=\sqrt{AC^2-\left(\frac{AB}{2}\right)^2}=\sqrt{"
        + bracket(a)
        + "^2-"
        + bracket(b / 2)
        + "^2}="
        + value(h)
    )


def _heron(m):
    a, b = m.given
    p = a + b / 2
    area = sp.simplify(b * sp.sqrt(a * a - b * b / 4) / 2)
    return (
        "<p>Чтобы найти площадь треугольника ABC, воспользуемся формулой Герона. Найдём полупериметр:</p>"
        + line(
            r"p=\frac{AB+AC+BC}{2}=\frac{"
            + value(b)
            + r"+2\cdot"
            + bracket(a)
            + "}{2}="
            + value(p)
        )
        + line(r"S=\sqrt{p(p-AC)(p-AB)(p-BC)}")
        + line(
            r"S=\sqrt{"
            + r"\cdot".join(bracket(v) for v in [p, p - a, p - b, p - a])
            + "}="
            + value(area)
        )
        + "<p>Далее по формуле радиуса описанной окружности находим:</p>"
        + line(r"R=\frac{abc}{4S}=\frac{AB\cdot AC\cdot BC}{4S}")
        + line(
            r"R=\frac{"
            + bracket(b)
            + r"\cdot"
            + bracket(a)
            + r"\cdot"
            + bracket(a)
            + r"}{4\cdot"
            + bracket(area)
            + "}="
            + value(m.answer)
        )
    )


def _sine(m):
    a, b = m.given
    h = sp.sqrt(a * a - b * b / 4)
    sine = sp.simplify(h / a)
    return (
        "<p><b>Приведем еще одно решение.</b></p><p>Проведём высоту CH треугольника ABC и найдём её из прямоугольного треугольника ACH:</p>"
        + _height(m)
        + line(
            r"\sin A=\frac{CH}{AC}=\frac{"
            + value(h)
            + "}{"
            + value(a)
            + "}="
            + value(sine)
        )
        + "<p>Применим теорему синусов к треугольнику ABC:</p>"
        + line(r"\frac{BC}{\sin A}=2R")
        + line(
            r"R=\frac{BC}{2\sin A}=\frac{"
            + value(a)
            + r"}{2\cdot"
            + bracket(sine)
            + "}="
            + value(m.answer)
        )
    )


def _center(m, picture):
    a, b = m.given
    h = sp.sqrt(a * a - b * b / 4)
    shape = kind(m)
    comparison = (
        "<p>Сравним квадрат основания с суммой квадратов боковых сторон:</p>"
        + line(
            r"AC^2+BC^2-AB^2=2\cdot"
            + bracket(a)
            + "^2-"
            + bracket(b)
            + "^2="
            + value(sp.simplify(2 * a * a - b * b))
        )
    )
    if shape == "right":
        return (
            picture
            + comparison
            + "<p>Разность равна нулю, поэтому треугольник ABC прямоугольный с прямым углом C. Центр описанной окружности O совпадает с серединой H гипотенузы AB.</p>"
            + _height(m)
            + line("OH=0")
            + line(r"R=AH=\frac{AB}{2}=\frac{" + value(b) + "}{2}=" + value(m.answer))
        )
    acute = shape == "acute"
    location = (
        "высоте CH внутри треугольника"
        if acute
        else "продолжении высоты CH за основание AB вне треугольника"
    )
    distance = "CH-R" if acute else "R-CH"
    numeric = bracket(h) + "-R" if acute else "R-" + bracket(h)
    return (
        picture
        + comparison
        + (
            "<p>Разность положительна, поэтому треугольник ABC "
            if acute
            else "<p>Разность отрицательна, поэтому треугольник ABC "
        )
        + ("остроугольный" if acute else "тупоугольный")
        + ". В равнобедренном треугольнике центр описанной окружности O лежит на "
        + location
        + ".</p>"
        + "<p>Проведём высоту CH и найдём её из прямоугольного треугольника ACH:</p>"
        + _height(m)
        + line("OH=" + distance)
        + "<p>Из прямоугольного треугольника AOH по теореме Пифагора получим:</p>"
        + line("R^2=AH^2+OH^2")
        + line("R^2=" + bracket(b / 2) + "^2+\\left(" + numeric + "\\right)^2")
        + line(
            r"2CH\cdot R=CH^2+AH^2="
            + bracket(h)
            + "^2+"
            + bracket(b / 2)
            + "^2="
            + value(a * a)
        )
        + line(
            r"R=\frac{CH^2+AH^2}{2CH}=\frac{"
            + value(a * a)
            + r"}{2\cdot"
            + bracket(h)
            + "}="
            + value(m.answer)
        )
    )


def _cosine(m):
    a, b = m.given
    cosine = sp.simplify((2 * a * a - b * b) / (2 * a * a))
    double = sp.simplify(2 * cosine**2 - 1)
    coefficient = sp.simplify(2 * (1 - double))
    central = (
        "Для тупого угла C меньший центральный угол AOB равен 360°−2C; его косинус равен косинусу 2C."
        if kind(m) == "obtuse"
        else "Центральный угол AOB равен удвоенному вписанному углу C."
    )
    cosine_theorem = (
        "По теореме косинусов для треугольника AOB:"
        if kind(m) != "right"
        else "При прямом угле C точки A, O и B лежат на одной прямой, AB — диаметр. Следующая запись также верна при центральном угле 180°:"
    )
    return (
        "<p>Запишем теорему косинусов для треугольника ABC, где основание AB противолежит вершине C:</p>"
        + line(r"AB^2=AC^2+BC^2-2AC\cdot BC\cos C")
        + line(
            r"\cos C=\frac{AC^2+BC^2-AB^2}{2AC\cdot BC}=\frac{2\cdot"
            + bracket(a)
            + "^2-"
            + bracket(b)
            + r"^2}{2\cdot"
            + bracket(a)
            + "^2}="
            + value(cosine)
        )
        + "<p>Зная косинус угла C, найдём косинус центрального угла. "
        + central
        + "</p>"
        + line(r"\cos\angle AOB=\cos 2C=2\cos^2 C-1=" + value(double))
        + line("AO=BO=R")
        + "<p>Отрезки AO и BO равны искомому радиусу. "
        + cosine_theorem
        + "</p>"
        + line(r"AB^2=AO^2+BO^2-2AO\cdot BO\cos\angle AOB")
        + line(
            bracket(b)
            + r"^2=2R^2\left(1-"
            + bracket(double)
            + r"\right)="
            + bracket(coefficient)
            + "R^2"
        )
        + line(
            r"R^2=\frac{"
            + bracket(b)
            + "^2}{"
            + value(coefficient)
            + "}="
            + value(m.answer**2)
        )
        + line(r"R=\sqrt{" + value(m.answer**2) + "}=" + value(m.answer))
    )


def render(m, pictures):
    picture = "<p>" + pictures["center"] + "</p>"
    return (
        solution_section("Решение", _heron(m) + picture + _sine(m))
        + solution_section("Альтернативное решение.", _center(m, picture))
        + solution_section("Альтернативное решение.", _cosine(m))
    )
