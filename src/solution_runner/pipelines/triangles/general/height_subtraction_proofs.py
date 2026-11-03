"""Expand the parent's subtraction of adjacent angles in the right triangle ACH."""

import hashlib

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..isosceles.angle_proofs import angle, degree
from ..right.altitude_methods import solution_section


def review_parent(html):
    if (
        not isinstance(html, str)
        or hashlib.sha256(html.encode()).hexdigest()
        != "f6b6e7431f00df967abe969d743d6dfdd18ee7c36c5eb6a7785c738ec5978cad"
    ):
        raise ContentPlanError("the reviewed height-angle subtraction method changed")


def render(m):
    a, ahc, ach, bch, acb = [
        angle(m.name(n)) for n in ["A", "AHC", "ACH", "BCH", "ACB"]
    ]
    return solution_section(
        "Решение",
        f"<p>{m.name('CH')} — высота, поэтому треугольник {m.name('ACH')} прямоугольный. Сначала найдём его угол при вершине {m.name('C')}:</p>"
        + line(ahc + r"=90^{\circ}")
        + line(ach + r"=90^{\circ}-" + a)
        + line(ach + r"=90^{\circ}-" + degree(m.alpha))
        + line(ach + "=" + degree(m.intermediate))
        + f"<p>На рисунке H лежит на продолжении {m.name('AB')} за {m.name('B')}. Луч {m.name('CB')} расположен внутри угла {m.name('ACH')}. Последовательно получаем:</p>"
        + line(acb + "=" + ach + "-" + bch)
        + line(acb + "=" + degree(m.intermediate) + "-" + degree(m.delta))
        + line(acb + "=" + degree(m.answer)),
    )
