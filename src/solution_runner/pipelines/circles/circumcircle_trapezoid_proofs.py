"""Keep perimeter/midline and three diameter proofs for cyclic trapezoids."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from ..triangles.right.altitude_methods import solution_section

MODES = {"trapezoid_leg", "trapezoid_radius"}
ISO = "<p>Трапеция ABCD равнобедренная, так как вокруг неё описана окружность.</p>"


def _leg(m):
    perimeter, midline = m.given
    bases = 2 * midline
    midline_term = bracket(midline) if midline.is_Add else value(midline)
    bases_term = bracket(bases) if bases.is_Add else value(bases)
    first = (
        ISO
        + "<p>Средняя линия равна полусумме оснований, значит, сумма оснований равна:</p>"
        + line("AB+CD=2FE=2\\cdot " + midline_term + "=" + value(bases))
        + "<p>Вычтем основания из периметра, чтобы найти сумму боковых сторон:</p>"
        + line(
            "AD+BC=P_{ABCD}-(AB+CD)="
            + value(perimeter)
            + "-"
            + bases_term
            + "="
            + value(perimeter - bases)
        )
        + "<p>Боковые стороны равны, поэтому каждая из них равна:</p>"
        + line("AD=BC=\\frac{" + value(perimeter - bases) + "}{2}=" + value(m.answer))
    )
    second = (
        ISO
        + "<p>Выразим боковую сторону через периметр и среднюю линию:</p>"
        + line(r"AD=\frac{P_{ABCD}-(AB+CD)}{2}")
        + line(r"AD=\frac{P_{ABCD}}{2}-\frac{AB+CD}{2}=\frac{P_{ABCD}}{2}-FE")
        + line(
            r"AD=\frac{"
            + value(perimeter)
            + "}{2}-"
            + midline_term
            + "="
            + value(perimeter / 2)
            + "-"
            + midline_term
            + "="
            + value(m.answer)
        )
    )
    return solution_section("Решение", first) + solution_section(
        "Приведем другое решение.", second
    )


def _radius(m, pictures):
    base = m.given[0]
    triangle = "<p>Окружность, описанная вокруг трапеции, описана и вокруг треугольника ADC. Он равнобедренный, поскольку AD=DC, угол при вершине D равен 120°, а углы при основании равны 30°.</p>"
    first = (
        pictures["projection"]
        + triangle
        + "<p>Найдём боковую сторону трапеции. Высота DH отсекает на основании отрезок AH; обе проекции боковых сторон равны:</p>"
        + line("AD=DC")
        + line(r"AH=AD\cos60^{\circ}=\frac{AD}{2}")
        + line("AD=AB-2AH=AB-AD=" + value(base) + "-AD")
        + line("2AD=AB=" + value(base))
        + line(r"AD=\frac{AB}{2}=\frac{" + value(base) + "}{2}=" + value(m.answer))
        + "<p>По теореме синусов в треугольнике ADC:</p>"
        + line(r"\angle DCA=\frac{180^{\circ}-120^{\circ}}{2}=30^{\circ}")
        + line(r"R=\frac{AD}{2\sin \angle DCA}")
        + line(
            r"R=\frac{"
            + value(m.answer)
            + r"}{2\sin30^{\circ}}=\frac{"
            + value(m.answer)
            + r"}{2\cdot\frac{1}{2}}="
            + value(m.answer)
        )
    )
    second = (
        "<p>Хорды AD, DC и CB равны, поэтому равны и стягиваемые ими дуги. Вписанный угол A равен 60°, он опирается на две из этих дуг и равен половине их суммы:</p>"
        + line(r"2\angle A=2\cdot60^{\circ}=120^{\circ}")
        + "<p>Поэтому каждая из трёх дуг равна 60°, а их сумма составляет:</p>"
        + line(r"3\cdot60^{\circ}=180^{\circ}")
        + "<p>Хорда AB является диаметром. Найдём радиус:</p>"
        + line("AB=2R")
        + line(r"R=\frac{AB}{2}=\frac{" + value(base) + "}{2}=" + value(m.answer))
    )
    third = (
        triangle
        + line(r"\angle DCB=180^{\circ}-60^{\circ}=120^{\circ}")
        + line(r"\angle DCA=\frac{180^{\circ}-120^{\circ}}{2}=30^{\circ}")
        + line(r"\angle ACB=\angle DCB-\angle DCA=120^{\circ}-30^{\circ}=90^{\circ}")
        + "<p>Угол ACB опирается на диаметр, поэтому AB — диаметр окружности:</p>"
        + line("AB=2R")
        + line(r"R=\frac{AB}{2}=\frac{" + value(base) + "}{2}=" + value(m.answer))
    )
    return (
        solution_section("Решение", first)
        + solution_section("Приведем другое решение (Р. А., СПб.).", second)
        + solution_section("Альтернативное решение.", third)
    )


def render(m, pictures):
    return _leg(m) if m.mode == "trapezoid_leg" else _radius(m, pictures)
