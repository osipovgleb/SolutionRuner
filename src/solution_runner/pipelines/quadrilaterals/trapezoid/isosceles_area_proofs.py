"""The parent's altitude, Pythagoras, area and perimeter calculations."""

from ...probability.common import line
from ..parallelogram.rectangle_proofs import bracket, value


def projection_rows(m, label="AH"):
    return line(label + r"=\frac{AD-BC}{2}") + line(
        label
        + r"=\frac{"
        + value(m.large)
        + "-"
        + value(m.small)
        + "}{2}="
        + value(m.projection)
    )


def height_rows(m, leg="AB", height="BH", projection="AH"):
    return (
        line(height + r"=\sqrt{" + leg + "^2-" + projection + "^2}")
        + line(
            height + r"=\sqrt{" + bracket(m.leg) + "^2-" + bracket(m.projection) + "^2}"
        )
        + line(height + r"=\sqrt{" + value(m.height**2) + "}=" + value(m.height))
    )


def _from_side(m):
    intro = "<p>Проведём высоту BH. В равнобедренной трапеции отрезок AH равен половине разности оснований:</p>"
    leg = (
        "<p>Трапеция равнобедренная, поэтому обе боковые стороны равны. Найдём каждую из данного периметра:</p>"
        + line(r"AB=\frac{P-(AD+BC)}{2}")
        + line(
            r"AB=\frac{"
            + value(m.given[2])
            + "-"
            + value(m.large + m.small)
            + "}{2}="
            + value(m.leg)
        )
        if m.mode == "perimeter_area"
        else line("AB=" + value(m.leg))
    )
    return (
        intro
        + projection_rows(m)
        + leg
        + "<p>По теореме Пифагора в прямоугольном треугольнике ABH найдём высоту, затем подставим её в формулу площади:</p>"
        + height_rows(m)
        + line(r"S=\frac{AD+BC}{2}\cdot BH")
        + line(
            r"S=\frac{"
            + value(m.large + m.small)
            + r"}{2}\cdot "
            + value(m.height)
            + "="
            + value(m.area)
        )
    )


def _from_area(m):
    result = (
        "<p>Найдём высоту BH из формулы площади трапеции:</p>"
        + line(r"S=\frac{AD+BC}{2}\cdot BH")
        + line(r"BH=\frac{2S}{AD+BC}")
        + line(
            r"BH=\frac{2\cdot "
            + value(m.area)
            + "}{"
            + value(m.large + m.small)
            + "}="
            + value(m.height)
        )
        + "<p>В равнобедренной трапеции AH равен полуразности оснований. Найдём боковую сторону AB по теореме Пифагора в треугольнике ABH:</p>"
        + line(r"AH=\frac{AD-BC}{2}=" + value(m.projection))
        + line(r"AB=\sqrt{BH^2+AH^2}")
        + line(
            r"AB=\sqrt{"
            + value(m.height**2)
            + "+"
            + value(m.projection**2)
            + "}="
            + value(m.leg)
        )
    )
    if m.requested == "perimeter":
        result += (
            "<p>Боковые стороны равны. Сложим обе найденные стороны и основания, чтобы получить периметр:</p>"
            + line("P=2AB+AD+BC")
            + line(
                r"P=2\cdot "
                + bracket(m.leg)
                + "+"
                + value(m.large)
                + "+"
                + value(m.small)
                + "="
                + value(m.perimeter)
            )
        )
    return result


def render(m):
    return _from_area(m) if m.mode == "area" else _from_side(m)
