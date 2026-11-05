"""Explain actual rectangular sections and witnessed pyramids rather than forcing a parent target."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def _midline(m):
    a, h = m.given
    return (
        "<p>Сечение — прямоугольник. Его сторона в основании является средней линией треугольника и равна половине стороны основания:</p>"
        + line(r"l=\frac{a}{2}")
        + line(r"l=\frac{" + value(a) + "}{2}=" + value(m.side))
        + "<p>Другая сторона прямоугольника равна боковому ребру прямой призмы:</p>"
        + line("H=" + value(h))
        + line("S=lH")
        + line("S=" + bracket(m.side) + r"\cdot" + bracket(h) + "=" + value(m.answer))
    )


def _median(m):
    a, h = m.given
    return (
        "<p>В правильном треугольнике основания медиана CE, проведённая к середине E стороны AB, является высотой. Обозначим её длину l и применим теорему Пифагора:</p>"
        + line(r"AE=\frac{a}{2}")
        + line(r"AE=\frac{" + value(a) + "}{2}=" + value(a / 2))
        + line("l^2=a^2-AE^2")
        + line(
            r"l=\sqrt{" + bracket(a) + "^2-" + bracket(a / 2) + "^2}=" + value(m.side)
        )
        + "<p>Сечение EE₁C₁C — прямоугольник с высотой, равной боковому ребру призмы:</p>"
        + line("S=lH")
        + line("S=" + bracket(m.side) + r"\cdot" + bracket(h) + "=" + value(m.answer))
    )


def _diagonal(m):
    h, d = m.given
    return (
        "<p>Диагональное сечение AA₁C₁C — прямоугольник. Пространственные диагонали правильной четырёхугольной призмы равны, поэтому обозначим их длину D, а длину AC — t:</p>"
        + line("D=BD_1=A_1C")
        + line("D^2=t^2+H^2")
        + line("t^2=D^2-H^2")
        + line(r"t=\sqrt{" + bracket(d) + "^2-" + bracket(h) + "^2}=" + value(m.side))
        + "<p>Площадь прямоугольника равна произведению его сторон:</p>"
        + line("S=Ht")
        + line("S=" + bracket(h) + r"\cdot" + bracket(m.side) + "=" + value(m.answer))
    )


def _vertex(m):
    solid = m.solid
    fraction = solid.fraction
    coefficient = 3 * solid.fraction
    name = "".join(solid.base).replace("_1", "₁")
    rows = (
        "<p>Искомый многогранник — пирамида с вершиной "
        + solid.apex.replace("_1", "₁")
        + " и основанием "
        + name
        + ". Найдём площадь этого основания и высоту, перпендикулярную его плоскости:</p>"
    )
    if solid.axis == 2:
        rows += line("B_p=" + value(coefficient) + "B") + line("h_p=H")
    else:
        rows += (
            line("B=a^2")
            + line(r"a=\sqrt{B}=\sqrt{" + value(m.area) + "}=" + value(m.side))
            + line("B_p=" + value(coefficient) + "aH")
            + line("h_p=a")
        )
    return (
        rows
        + "<p>Объём пирамиды равен трети произведения площади основания на высоту. Выразим его через площадь основания и высоту призмы:</p>"
        + line(r"V=\frac{1}{3}B_ph_p")
        + line("V=" + bracket(fraction) + "BH")
        + line(
            "V="
            + bracket(fraction)
            + r"\cdot"
            + bracket(m.area)
            + r"\cdot"
            + bracket(m.height)
        )
        + line("V=" + value(m.answer))
    )


METHODS = {
    "midline_section": _midline,
    "median_section": _median,
    "diagonal_section": _diagonal,
    "vertex_volume": _vertex,
}


def render(m):
    return METHODS[m.kind](m)
