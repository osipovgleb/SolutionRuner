"""Adapt the two reviewed additional side-altitude methods to each child's values."""

import sympy as sp

from ...probability.common import line
from ..right.altitude_parent import exact_answer
from .side_altitude_proofs import angle, number, trig


def side_sine_height(model):
    p, r = model.vertex, model.apex
    base = model.base_segment
    half = p + "K"
    side = model.side_segment
    t = model.triangle
    name = trig("cos", r + p + "K")
    body = f"<p>Проведем из вершины {r} высоту {r + 'K'}. Тогда:</p>"
    body += line(name + r"=\frac{" + half + "}{" + side + "}")
    body += line(
        name
        + r"=\sqrt{1-("
        + trig("sin", r + p + "K")
        + r")^2}=\sqrt{1-("
        + t.function_latex
        + ")^2}="
        + number(t.cosine)
    )
    body += "<p>Поэтому:</p>" + line(
        half
        + "="
        + side
        + name
        + "=("
        + t.length_latex
        + r")\cdot("
        + number(t.cosine)
        + ")="
        + number(t.base / 2)
    )
    body += line(
        base + "=2" + half + r"=2\cdot(" + number(t.base / 2) + ")=" + number(t.base)
    )
    body += "<p>Следовательно, искомая высота:</p>" + line(
        model.height_segment
        + "="
        + trig("sin", angle(model))
        + base
        + "=("
        + t.function_latex
        + r")\cdot("
        + number(t.base)
        + ")="
        + exact_answer(model.answer).replace(",", "{,}")
    )
    return body


def cosine_projection(model):
    p, q, r = model.vertex, model.other_base_vertex, model.apex
    base = model.base_segment
    side = model.side_segment
    other = "".join(sorted((q, r)))
    projection = model.projection_segment
    height = model.height_segment
    t = model.triangle
    answer = exact_answer(model.answer).replace(",", "{,}")
    if t.cosine == sp.Rational(1, 2):
        return (
            "<p>По условию косинус угла при основании равен 0,5, значит:</p>"
            + line(r"\angle " + angle(model) + r"=60^{\circ}")
            + f"<p>Треугольник ABC равносторонний. Высота {height} является и медианой, поэтому делит сторону {other} пополам:</p>"
            + line(
                projection
                + r"=\frac{"
                + other
                + r"}{2}=\frac{"
                + base
                + r"}{2}=\frac{"
                + t.length_latex
                + "}{2}="
                + answer
            )
        )
    body = "<p>Используем равенство боковых сторон. По теореме косинусов:</p>"
    body += line(
        side
        + "^2="
        + base
        + "^2+"
        + other
        + "^2-2"
        + base
        + other
        + trig("cos", p + q + r)
    )
    body += line(
        other
        + r"=\frac{"
        + base
        + "}{2"
        + trig("cos", angle(model))
        + r"}=\frac{"
        + t.length_latex
        + r"}{2\cdot("
        + t.function_latex
        + ")}="
        + number(t.side)
    )
    body += f"<p>Выразим квадраты расстояний через высоту {height} и проекцию {projection}. Квадрат разности подходит и для основания высоты на продолжении стороны:</p>"
    body += line(base + "^2=" + height + "^2+" + projection + "^2")
    body += line(side + "^2=" + height + "^2+(" + other + "-" + projection + ")^2")
    body += f"<p>Вычтем равенства и учтем, что {side} = {other}:</p>"
    body += line("2" + other + projection + "=" + base + "^2")
    body += line(
        projection
        + r"=\frac{"
        + base
        + "^2}{2"
        + other
        + r"}=\frac{("
        + t.length_latex
        + r")^2}{2\cdot("
        + number(t.side)
        + ")}="
        + answer
    )
    return body
