"""Keep the parent's method order and both sixty-degree perimeter arguments."""

from ...probability.common import line
from ...triangles.right.altitude_methods import solution_section
from ..parallelogram.rectangle_proofs import bracket, value
from .isosceles_area_proofs import projection_rows
from .isosceles_area_proofs import render as area_proof
from .isosceles_trig_proofs import render as trig_proof


def _sixty(m, picture):
    first = (
        picture
        + "<p>Проведём высоту BH. В равнобедренной трапеции AH равен полуразности оснований:</p>"
        + projection_rows(m)
        + "<p>Боковая сторона AB равна отношению AH к косинусу острого угла. Подставим это выражение в формулу периметра:</p>"
        + line("P=AD+BC+2AB")
        + line(r"P=AD+BC+\frac{2AH}{\cos\angle BAD}")
        + line(r"\cos60^{\circ}=\frac{1}{2}")
        + line(
            "P="
            + value(m.large + m.small)
            + r"+\frac{"
            + value(2 * m.projection)
            + r"}{\frac{1}{2}}"
        )
        + line("P=" + value(m.perimeter))
    )
    second = (
        "<p>Высота равнобокой трапеции, опущенная на большее основание, делит его на больший отрезок, равный полусумме оснований, и меньший, равный их полуразности. Проведём высоту BH; меньшим отрезком является AH:</p>"
        + projection_rows(m)
        + "<p>В прямоугольном треугольнике ABH второй острый угол равен 30°. Катет против этого угла равен половине гипотенузы:</p>"
        + line(r"\angle ABH=90^{\circ}-60^{\circ}=30^{\circ}")
        + line(r"AH=\frac{AB}{2}")
        + line(r"AB=2AH=2\cdot " + bracket(m.projection) + "=" + value(m.leg))
        + "<p>Боковые стороны трапеции равны. Найдём периметр:</p>"
        + line("CD=AB")
        + line(
            "P=AD+BC+AB+CD="
            + value(m.large)
            + "+"
            + value(m.small)
            + "+"
            + value(m.leg)
            + "+"
            + value(m.leg)
            + "="
            + value(m.perimeter)
        )
    )
    return solution_section("Решение", first) + solution_section(
        "Приведем другое решение", second
    )


def render(m, pictures):
    picture = pictures.get("height", "")
    if m.mode == "perimeter_sixty":
        return _sixty(m, picture)
    proof = (
        area_proof(m)
        if m.mode in {"perimeter_area", "side_area", "area"}
        else trig_proof(m)
    )
    return solution_section("Решение", picture + proof)
