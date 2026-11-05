"""Preserve face, two-stage and projected Pythagorean distance methods."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import value
from .orthogonal_element_geometry import squared
from .orthogonal_element_terms import leaf_rows, name


def construction(m):
    if m.right != "K":
        return ""
    k = m.points["K"]
    vertical = next((n for n in m.names if m.points[n][:2] == k[:2]), None)
    if vertical:
        return (
            "Опустим перпендикуляр "
            + name(vertical + "K")
            + " на плоскость основания. "
        )
    parallel = next(n for n in m.names if m.points[n][1:] == k[1:])
    return (
        "Через вершину "
        + name(parallel)
        + " проведём отрезок "
        + name("K" + parallel)
        + ", параллельный ребру "
        + name("AB")
        + ", до пересечения с ребром "
        + name("AA_2")
        + " в точке K. "
    )


def render(m, picture):
    a, b = m.names
    right = m.right
    triangle = a + right + b
    introduction = "<p>" + construction(m)
    introduction += (
        "Рассмотрим прямоугольный треугольник "
        + name(triangle)
        + ". Все двугранные углы тела прямые, поэтому его катеты перпендикулярны.</p>"
    )
    first, second = a + right, right + b
    s1, s2 = squared(m.points, first), squared(m.points, second)
    total = s1 + s2
    html = (
        introduction
        + picture
        + "<p>Выразим длины катетов по отмеченным размерам. Если катет является диагональю прямоугольника, ещё раз применим теорему Пифагора:</p>"
    )
    html += leaf_rows(m, a, right) + leaf_rows(m, right, b)
    label = m.requested + "^2"
    html += (
        "<p>Применим теорему Пифагора к выбранному треугольнику:</p>"
        + line(label + "=" + first + "^2+" + second + "^2")
        + line(label + "=" + value(s1) + "+" + value(s2))
        + line(label + "=" + value(total))
    )
    if m.mode == "distance":
        html += line(m.requested + r"=\sqrt{" + value(total) + "}=" + value(m.value))
    return html
