"""Keep angle-sum and central-isosceles-triangle methods and image placement."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import value
from ..triangles.right.altitude_methods import solution_section


def render(model, pictures):
    angle = model.given[0]
    central = 180 - angle
    first = (
        "<p>Сумма углов n-угольника равна 180°(n−2). Каждый из них равен данному углу α, поэтому, с другой стороны, эта сумма равна αn. Решим полученное уравнение:</p>"
        + line(r"180^{\circ}(n-2)=\alpha n")
        + line(r"180^{\circ}n-360^{\circ}=" + value(angle) + r"^{\circ}n")
        + line(r"(180^{\circ}-" + value(angle) + r"^{\circ})n=360^{\circ}")
        + line(value(central) + r"^{\circ}n=360^{\circ}")
        + line(r"n=\frac{360}{" + value(central) + "}=" + value(model.answer))
        + pictures["polygon"]
    )
    second = (
        "<p>Рассмотрим равнобедренный треугольник AOB, где A и B — соседние вершины многоугольника, O — центр окружности. Углы при его основании равны половине угла многоугольника:</p>"
        + line(
            r"\angle OAB=\angle ABO=\frac{\alpha}{2}=\frac{"
            + value(angle)
            + r"^{\circ}}{2}="
            + value(angle / 2)
            + r"^{\circ}"
        )
        + line(r"\angle AOB=180^{\circ}-2\angle OAB")
        + line(
            r"\angle AOB=180^{\circ}-"
            + value(angle)
            + r"^{\circ}="
            + value(central)
            + r"^{\circ}"
        )
        + "<p>Все центральные углы равны, а их сумма составляет полный угол. Найдём число вершин:</p>"
        + line(r"n=\frac{360^{\circ}}{\angle AOB}")
        + line(r"n=\frac{360}{" + value(central) + "}=" + value(model.answer))
    )
    return solution_section("Решение", first) + solution_section(
        "Приведём другое решение.", second
    )
