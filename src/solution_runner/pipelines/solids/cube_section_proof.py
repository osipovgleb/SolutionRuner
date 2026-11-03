"""Retain the parent's congruent-right-triangles proof of the section angle."""

from ..probability.common import line


def render(m, pictures):
    corner = m.corner.replace("_1", "<sub>1</sub>")
    triangles = corner + "KM, KL" + corner + " и L" + corner + "M"
    return (
        "<p>"
        + pictures["section"]
        + "Стороны сечения KM, KL и LM равны как гипотенузы равных прямоугольных треугольников "
        + "<i>"
        + triangles
        + "</i>, которые равны друг другу по двум катетам: каждый катет равен половине ребра куба.</p>"
        + line("KM=KL=LM")
        + "<p>Таким образом, треугольник LKM является равносторонним. Все его углы равны, поэтому искомый угол равен:</p>"
        + line(r"\angle " + m.angle + r"=\frac{180^{\circ}}{3}=60^{\circ}")
    )
