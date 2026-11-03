"""Preserve the convex-quadrilateral method for both two-altitude groups."""

import hashlib

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..isosceles.angle_proofs import angle, degree
from ..right.altitude_methods import solution_section

PARENTS = {
    "general-triangle-27762-orthocenter-angle": "a6d8c53788a277ef8faad2d4ebbd6a37223ba7e14e3a25027c23a0d94e53011f",
    "general-triangle-500142-altitudes-obtuse-angle": "02935f4740d37a9884a652333a606ab05c4f4dd672222a71fb779a3f92c5804d",
}


def review_parent(html, rule):
    if not isinstance(html, str) or hashlib.sha256(
        html.encode()
    ).hexdigest() != PARENTS.get(rule):
        raise ContentPlanError(
            "the complete altitude-quadrilateral parent method must be reviewed"
        )


def render(m):
    a, d, e, target = (angle(m.name(n)) for n in ("A", "ADO", "OEA", "DOE"))
    outside = (
        f"<p>Угол {m.name('A')} тупой, поэтому основания D и E лежат на продолжениях сторон за вершину {m.name('A')}. Оба луча угла D{m.name('A')}E противоположны соответствующим сторонам треугольника, поэтому этот угол равен данному.</p>"
        if m.alpha > 90
        else ""
    )
    return solution_section(
        "Решение",
        f"<p>Отрезки {m.name('BD')} и {m.name('CE')} — высоты. Углы при их основаниях прямые:</p>"
        + line(d + r"=90^{\circ}")
        + line(e + r"=90^{\circ}")
        + outside
        + line(angle(m.name("DAE")) + "=" + a)
        + f"<p>Сумма углов выпуклого четырёхугольника {m.name('ADOE')} равна 360°. Вычтем три известных угла и найдем искомый:</p>"
        + line(target + r"=360^{\circ}-" + d + "-" + e + "-" + a)
        + line(target + r"=360^{\circ}-90^{\circ}-90^{\circ}-" + degree(m.alpha))
        + line(target + r"=180^{\circ}-" + degree(m.alpha))
        + line(target + "=" + degree(m.answer)),
    )
