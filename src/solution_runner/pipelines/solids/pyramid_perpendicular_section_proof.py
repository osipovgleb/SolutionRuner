"""Compare the sum of the two tetrahedral volumes with the pyramid volume."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts
from .spatial_metric_proofs import picture


def render(m, pictures):
    q = m.q
    first = (
        "<p>Пусть SO — высота пирамиды. Проекция SC на основание — CO, причём CO ⟂ AB. По теореме о трёх перпендикулярах SC ⟂ AB. В треугольнике BCS проведём высоту BK к SC. Тогда SC перпендикулярна двум пересекающимся прямым AB и BK, поэтому искомое сечение — треугольник ABK.</p>"
        + "<p>Обозначим площадь ABK через Q. Сечение разбивает пирамиду на тетраэдры CAKB и SAKB. Их высоты к общему основанию ABK равны CK и SK:</p>"
        + line(r"V=\frac{1}{3}Q\cdot CK+\frac{1}{3}Q\cdot SK")
        + line(r"V=\frac{1}{3}Q(CK+SK)=\frac{1}{3}Q\cdot SC")
        + line(r"3V=Q\cdot SC")
    )
    if m.names[0] == "ratio":
        first += (
            "<p>С другой стороны, объём равен трети произведения площади основания и высоты:</p>"
            + line(r"V=\frac{1}{3}SO\cdot S_{ABC}")
            + line(r"Q\cdot SC=SO\cdot S_{ABC}")
            + line(r"\frac{Q}{S_{ABC}}=\frac{SO}{SC}")
        )
    second = (
        "<p>В прямоугольном треугольнике SCO найдём высоту SO:</p>"
        + line(
            r"CO=\frac{AB}{\sqrt{3}}=\frac{"
            + value(q["a"])
            + r"}{\sqrt{3}}="
            + value(q["R"])
        )
        + line(
            r"SO=\sqrt{SC^2-CO^2}=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["R"])
            + "^2}="
            + value(q["H"])
        )
        + "<p>Основание — равносторонний треугольник. Вычислим его площадь и объём пирамиды:</p>"
        + line(
            r"S_{ABC}=\frac{AB^2\sqrt{3}}{4}=\frac{"
            + bracket(q["a"])
            + r"^2\sqrt{3}}{4}="
            + value(q["B"])
        )
        + line(
            r"V=\frac{1}{3}SO\cdot S_{ABC}=\frac{1}{3}\cdot "
            + bracket(q["H"])
            + r"\cdot "
            + bracket(q["B"])
            + "="
            + value(q["V"])
        )
        + "<p>Приравнивая два выражения для объёма, получаем площадь сечения:</p>"
        + line(
            r"Q=\frac{3V}{SC}=\frac{3\cdot "
            + bracket(q["V"])
            + "}{"
            + value(q["e"])
            + "}="
            + value(m.answer)
        )
        + "<p><b>Примечание.</b> Сравниваются два выражения объёма: через площадь основания и высоту и через площадь перпендикулярного сечения и боковое ребро.</p>"
    )
    return picture(pictures) + parts(first, second)
