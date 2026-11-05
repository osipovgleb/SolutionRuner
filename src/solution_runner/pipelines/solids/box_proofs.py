"""Expand reviewed box methods and repair the parent's broken radical scope."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from . import box_face_proofs
from .box_model import FACE_MODES

SURFACE = "S=2(a_1a_2+a_1a_3+a_2a_3)"
DIAGONAL = r"d=\sqrt{a_1^2+a_2^2+a_3^2}"


def _products(m):
    a, b, c = m.edges
    return (
        bracket(a)
        + r"\cdot"
        + bracket(b)
        + "+"
        + bracket(a)
        + r"\cdot"
        + bracket(c)
        + "+"
        + bracket(b)
        + r"\cdot"
        + bracket(c)
    )


def _surface(m):
    a, b, c = m.edges
    return (
        line(SURFACE)
        + line("S=2(" + _products(m) + ")")
        + line("S=2(" + value(a * b) + "+" + value(a * c) + "+" + value(b * c) + ")")
        + line("S=" + value(2 * (a * b + a * c + b * c)))
    )


def _diagonal(m):
    a, b, c = m.edges
    return (
        line(DIAGONAL)
        + line(
            r"d=\sqrt{" + bracket(a) + "^2+" + bracket(b) + "^2+" + bracket(c) + "^2}"
        )
        + line("d=" + value(sp.sqrt(a * a + b * b + c * c)))
    )


def _surface_edge(m):
    a, b, c = m.edges
    s = m.given[2]
    return (
        "<p>Пусть неизвестное ребро равно x. Площадь поверхности параллелепипеда выражается через три ребра:</p>"
        + line("S=2(a_1a_2+a_1x+a_2x)")
        + line(
            "2("
            + bracket(a)
            + r"\cdot"
            + bracket(b)
            + "+"
            + bracket(a)
            + "x+"
            + bracket(b)
            + "x)="
            + value(s)
        )
        + "<p>Раскроем выражение и решим линейное уравнение:</p>"
        + line(value(a * b) + "+" + bracket(a + b) + r"x=\frac{" + value(s) + "}{2}")
        + line(bracket(a + b) + r"x=\frac{" + value(s) + "}{2}-" + bracket(a * b))
        + line(
            r"x=\frac{"
            + value(s)
            + r"/2-"
            + bracket(a * b)
            + "}{"
            + value(a + b)
            + "}="
            + value(c)
        )
    )


def _surface_note(m):
    a, b, c = m.edges
    s = m.given[2]
    return (
        "<p><b>Примечание о том, как не надо решать эту задачу.</b></p>"
        + "<p>Если сначала выполнять все преобразования в буквенном виде, получится тот же результат. Подстановка чисел в начале позволяет сократить выкладки. Обозначим известные рёбра a₁ и a₂, неизвестное — a₃:</p>"
        + line(SURFACE)
        + line(r"a_3(a_1+a_2)=\frac{S}{2}-a_1a_2")
        + line(r"a_3=\frac{S/2-a_1a_2}{a_1+a_2}")
        + line(
            r"a_3=\frac{"
            + value(s)
            + r"/2-"
            + bracket(a)
            + r"\cdot"
            + bracket(b)
            + "}{"
            + value(a)
            + "+"
            + value(b)
            + "}="
            + value(c)
        )
        + "<p>Теперь найдём диагональ по трём измерениям:</p>"
        + _diagonal(m)
    )


def _volume_edge(m):
    a, b, c = m.edges
    v = m.given[2]
    return (
        "<p>Объём прямоугольного параллелепипеда равен произведению его измерений. Найдём третье ребро:</p>"
        + line("V=a_1a_2a_3=" + value(v))
        + line(r"a_3=\frac{V}{a_1a_2}")
        + line(
            r"a_3=\frac{"
            + value(v)
            + "}{"
            + bracket(a)
            + r"\cdot"
            + bracket(b)
            + "}="
            + value(c)
        )
    )


def _edge_volume(m):
    a, b, c = m.edges
    v = m.given[2]
    return (
        "<p>Объём параллелепипеда равен произведению трёх измерений. Пусть неизвестное ребро равно x:</p>"
        + line("V=a_1a_2x")
        + line(bracket(a) + r"\cdot" + bracket(b) + "x=" + value(v))
        + line(bracket(a * b) + "x=" + value(v))
        + "<p>Разделим на произведение известных рёбер:</p>"
        + line(r"x=\frac{" + value(v) + "}{" + bracket(a) + r"\cdot" + bracket(b) + "}")
        + line("x=" + value(c))
    )


def _diagonal_edge(m):
    a, b, c = m.edges
    d = m.given[2]
    first = DIAGONAL if m.mode == "volume_from_diagonal" else "d^2=a_1^2+a_2^2+a_3^2"
    return (
        "<p>Диагональ прямоугольного параллелепипеда связана с его измерениями теоремой Пифагора:</p>"
        + line(first)
        + line(bracket(d) + "^2=" + bracket(a) + "^2+" + bracket(b) + "^2+a_3^2")
        + "<p>Выразим третье ребро. Длина ребра положительна:</p>"
        + line("a_3^2=" + bracket(d) + "^2-" + bracket(a) + "^2-" + bracket(b) + "^2")
        + line("a_3^2=" + value(c * c))
        + line(r"a_3=\sqrt{" + value(c * c) + "}=" + value(c))
    )


def _volume(m):
    a, b, c = m.edges
    return line("V=a_1a_2a_3") + line(
        "V="
        + bracket(a)
        + r"\cdot"
        + bracket(b)
        + r"\cdot"
        + bracket(c)
        + "="
        + value(a * b * c)
    )


def _cube(m):
    a, b, c = m.edges
    v = sp.simplify(a * b * c)
    return (
        "<p>Объём куба равен объёму данного параллелепипеда. Найдём этот объём как произведение трёх измерений:</p>"
        + line("V=a_1a_2a_3")
        + line("V=" + bracket(a) + r"\cdot" + bracket(b) + r"\cdot" + bracket(c))
        + line("V=" + value(v))
        + "<p>Обозначим ребро равновеликого куба через a. Его объём равен кубу ребра:</p>"
        + line("a^3=V")
        + "<p>Извлечём кубический корень:</p>"
        + line(r"a=\sqrt[3]{" + value(v) + "}=" + value(m.answer))
    )


def render(m):
    if m.mode in FACE_MODES:
        return box_face_proofs.render(m)
    if m.mode in {"edge_from_surface", "diagonal_from_surface"}:
        common = _surface_edge(m)
        return (
            common
            if m.mode == "edge_from_surface"
            else common
            + "<p>Найдём диагональ по трём измерениям:</p>"
            + _diagonal(m)
            + _surface_note(m)
        )
    if m.mode == "edge_from_volume":
        return _edge_volume(m)
    if m.mode == "cube_edge_from_edges":
        return _cube(m)
    if m.mode in {"diagonal_from_volume", "surface_from_volume"}:
        return _volume_edge(m) + (
            "<p>Найдём диагональ по трём измерениям:</p>" + _diagonal(m)
            if m.mode == "diagonal_from_volume"
            else "<p>Найдём площадь поверхности как удвоенную сумму площадей трёх граней:</p>"
            + _surface(m)
        )
    if m.mode in {"volume_from_diagonal", "surface_from_diagonal"}:
        return _diagonal_edge(m) + (
            "<p>Найдём объём как произведение измерений:</p>" + _volume(m)
            if m.mode == "volume_from_diagonal"
            else "<p>Найдём площадь поверхности:</p>" + _surface(m)
        )
    return (
        "<p>Площадь поверхности прямоугольного параллелепипеда равна удвоенной сумме попарных произведений его измерений:</p>"
        + _surface(m)
    )
