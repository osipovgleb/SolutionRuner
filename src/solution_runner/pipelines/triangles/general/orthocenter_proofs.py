"""Expand the parent's perpendicular-lines argument in the right triangle AOF."""

import hashlib

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..isosceles.angle_proofs import angle, degree
from ..right.altitude_methods import solution_section


def review_parent(html):
    if (
        not isinstance(html, str)
        or hashlib.sha256(html.encode()).hexdigest()
        != "335b0e8812cce6c6854a496bae86145eec2d2338c2ab1db89aaa5fb0db168085"
    ):
        raise ContentPlanError(
            "the reviewed perpendicular-altitudes parent method changed"
        )


def render(m):
    b, afo, oaf, aof = [angle(m.name(n)) for n in ["B", "AFO", "OAF", "AOF"]]
    complement = 90 - m.answer
    relation = r"90^{\circ}-" + b if m.beta < 90 else b + r"-90^{\circ}"
    substitution = (
        r"90^{\circ}-" + degree(m.beta)
        if m.beta < 90
        else degree(m.beta) + r"-90^{\circ}"
    )
    extension = (
        "При тупом угле треугольника рассматриваем прямые, содержащие высоты, и их показанные на рисунке продолжения. "
        if max(m.alpha, m.beta, m.gamma) > 90
        else ""
    )
    difference = (
        f"прямого угла и угла {m.name('B')}"
        if m.beta < 90
        else f"угла {m.name('B')} и прямого угла"
    )
    return solution_section(
        "Решение",
        f"<p>Острый угол между прямыми, содержащими высоты, равен острому углу между перпендикулярными им сторонами. Раскроем это свойство: {m.name('AD')} перпендикулярна {m.name('BC')}, а {m.name('CF')} — {m.name('AB')}. {extension}Треугольник {m.name('AOF')} прямоугольный. Его острый угол при {m.name('A')} равен разности {difference}:</p>"
        + line(afo + r"=90^{\circ}")
        + line(oaf + "=" + relation)
        + line(oaf + "=" + substitution)
        + line(oaf + "=" + degree(complement))
        + f"<p>Используем сумму углов треугольника {m.name('AOF')}, чтобы получить искомый угол:</p>"
        + line(aof + r"=180^{\circ}-" + afo + "-" + oaf)
        + line(aof + r"=180^{\circ}-90^{\circ}-" + degree(complement))
        + line(aof + "=" + degree(m.answer)),
    )
