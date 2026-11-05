"""Follow the parent's parallel-faces, rectangle, Pythagoras and area method."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .distance_proofs import _face, given, html_name, label, length


def render(m, picture):
    a, b, d, e = m.vertices
    rectangle = "".join(m.vertices)
    edge, diagonal = label(m.edge), label(m.diagonal)
    actual, amount = given(m, m.edge)
    return (
        "<p>"
        + picture
        + "Сечение пересекает параллельные грани по параллельным отрезкам. Поэтому сечение "
        + html_name(rectangle)
        + " — параллелограмм. Кроме того, ребро "
        + html_name(edge)
        + " перпендикулярно граням, содержащим стороны "
        + html_name(label(a + e))
        + " и "
        + html_name(label(b + d))
        + ". Поэтому углы "
        + html_name(e + a + b)
        + " и "
        + html_name(a + b + d)
        + " — прямые. Следовательно, сечение "
        + html_name(rectangle)
        + " — прямоугольник.</p>"
        + "<p>Из прямоугольного треугольника "
        + html_name(a + m.right + e)
        + " найдём "
        + html_name(diagonal)
        + " по теореме Пифагора. Параллельные рёбра параллелепипеда равны:</p>"
        + _face(m, m.diagonal, (a + m.right, m.right + e), root=True)
        + "<p>Площадь прямоугольника равна произведению соседних сторон:</p>"
        + line(
            edge
            + ("=" + label(actual) if label(actual) != edge else "")
            + "="
            + value(amount)
        )
        + line("S=" + edge + r"\cdot " + diagonal)
        + line(
            "S="
            + bracket(length(m, m.edge))
            + r"\cdot"
            + bracket(length(m, m.diagonal))
            + "="
            + value(m.answer)
        )
    )
