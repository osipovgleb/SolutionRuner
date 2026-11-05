"""Similar triangles, their areas and the trapezoid's spatial height."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _midpoint(m, pictures):
    q = m.q
    first = (
        pictures.get("image_1", "")
        + "<p>Основания трапеции AN и MK лежат в параллельных основаниях призмы. Поскольку M и K — внутренние точки верхних рёбер, меньшее основание — MK. Стороны треугольников MB₁K и ABN соответственно параллельны. Следовательно, треугольники подобны:</p>"
        + line(
            r"k=\frac{MK}{AN}=\frac{"
            + value(q["small"])
            + "}{"
            + value(q["large"])
            + "}="
            + value(q["ratio"])
        )
        + line(r"\frac{B_1K}{BN}=k,\qquad \frac{B_1K}{B_1C_1}=" + value(q["fraction"]))
        + line(
            r"BN=\frac{B_1K}{k}=\frac{"
            + bracket(q["fraction"])
            + "}{"
            + value(q["ratio"])
            + r"}B_1C_1=\frac{B_1C_1}{2}=\frac{BC}{2}"
        )
        + "<p>Таким образом, N — середина BC.</p>"
    )
    return first


def _quantity(m):
    q = m.q
    return (
        "<p>Высота прямой призмы равна её боковому ребру. Из объёма найдём площадь основания:</p>"
        + line(
            r"S_{ABCD}=\frac{V}{h}=\frac{"
            + value(q["volume"])
            + "}{"
            + value(q["height"])
            + "}="
            + value(q["base"])
        )
        + "<p>Поскольку N — середина BC, площадь треугольника ABN составляет четверть площади параллелограмма ABCD. Площади подобных треугольников относятся как квадрат коэффициента подобия:</p>"
        + line(
            r"S_{ABN}=\frac{S_{ABCD}}{4}=\frac{"
            + value(q["base"])
            + "}{4}="
            + value(q["triangle"])
        )
        + line(
            r"S_{MB_1K}=k^2S_{ABN}="
            + bracket(q["ratio"])
            + r"^2\cdot "
            + bracket(q["triangle"])
            + "="
            + value(q["upper_triangle"])
        )
        + "<p>Пусть BH и B₁H₁ — высоты этих треугольников к основаниям AN и MK. Тогда:</p>"
        + line(
            r"BH=\frac{2S_{ABN}}{AN}=\frac{2\cdot "
            + bracket(q["triangle"])
            + "}{"
            + value(q["large"])
            + "}="
            + value(q["BH"])
        )
        + line(
            r"B_1H_1=k\cdot BH="
            + bracket(q["ratio"])
            + r"\cdot "
            + bracket(q["BH"])
            + "="
            + value(q["B1H1"])
        )
        + "<p>Из подобия треугольников и параллельности соответствующих сторон проекция H₁ на основание призмы лежит на BH. Горизонтальная составляющая HH₁ равна BH − B₁H₁, а вертикальная — BB₁. По теореме Пифагора:</p>"
        + line(
            r"BH-B_1H_1="
            + value(q["BH"])
            + "-"
            + bracket(q["B1H1"])
            + "="
            + value(q["difference"])
        )
        + line(
            r"HH_1=\sqrt{BB_1^2+(BH-B_1H_1)^2}=\sqrt{"
            + bracket(q["height"])
            + "^2+"
            + bracket(q["difference"])
            + "^2}="
            + value(q["altitude"])
        )
        + "<p>По теореме о трёх перпендикулярах HH₁ перпендикулярен AN. Это высота трапеции AMKN, поэтому:</p>"
        + line(r"S_{AMKN}=\frac{MK+AN}{2}\cdot HH_1")
        + line(
            r"S_{AMKN}=\frac{"
            + value(q["small"])
            + "+"
            + value(q["large"])
            + r"}{2}\cdot "
            + bracket(q["altitude"])
            + "="
            + value(m.answer)
        )
    )


def render(m, pictures):
    return parts(_midpoint(m, pictures), _quantity(m))
