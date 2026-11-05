"""Keep face Pythagoras and prove equal perpendicular legs before finding the angle."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import value
from . import box_coordinates as c
from .box_distance_geometry import face_corner
from .distance_proofs import _face, given, html_name, label


def render(m, picture):
    prefix = "<p>" + picture + "</p>" if picture else ""
    diagonal = next((s for s in m.legs if len(c.axes(s)) == 2), None)
    if diagonal:
        a, b = c.endpoints(diagonal)
        corner = face_corner(a, b)
        fourth = next(
            n
            for n, p in c.VERTICES.items()
            if p
            == tuple(
                x + y - z
                for x, y, z in zip(c.VERTICES[a], c.VERTICES[b], c.VERTICES[corner])
            )
        )
        plane = a + corner + b + fourth
        edge = next(v for v in m.legs if len(c.axes(v)) == 1)
        perpendicular = (
            "Ребро "
            + html_name(label(edge))
            + " перпендикулярно плоскости грани "
            + html_name(plane)
            + ", поэтому угол при вершине "
            + html_name(m.right)
            + " прямой. "
        )
        body = (
            "<p>В прямоугольнике "
            + html_name(a + corner + b + fourth)
            + " найдём диагональ "
            + html_name(label(diagonal))
            + " по теореме Пифагора. Используем равенство параллельных рёбер:</p>"
            + _face(m, diagonal, (a + corner, corner + b), root=True)
        )
    else:
        perpendicular = "Катеты являются смежными рёбрами прямоугольной грани, поэтому угол между ними прямой. "
        body = "<p>Катеты рассматриваемого треугольника являются смежными рёбрами прямоугольного параллелепипеда. Выразим их длины через данные условия:</p>"
        for segment in m.legs:
            name, amount = given(m, segment)
            body += line(
                label(segment)
                + ("=" + label(name) if label(name) != label(segment) else "")
                + "="
                + value(amount)
            )
    first, second = (label(s) for s in m.legs)
    length = sp.sqrt(c.squared_length(m.legs[0], m.squares))
    other = [v for v in m.vertices if v != m.right]
    right_angle = other[0] + m.right + other[1]
    return (
        prefix
        + body
        + "<p>"
        + perpendicular
        + "Катеты равны:</p>"
        + line(first + "=" + second + "=" + value(length))
        + "<p>Следовательно, треугольник "
        + html_name("".join(m.vertices))
        + " прямоугольный и равнобедренный. Его острые углы равны, а их сумма равна 90°:</p>"
        + line(r"\angle " + right_angle + r"=90^{\circ}")
        + line(r"2\cdot\angle " + m.requested + r"=180^{\circ}-90^{\circ}=90^{\circ}")
        + line(r"\angle " + m.requested + r"=\frac{90^{\circ}}{2}=45^{\circ}")
    )
