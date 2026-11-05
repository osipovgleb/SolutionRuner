"""Use the actual edge-plane and base angles to distinguish edge length from height."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def render(m, picture=""):
    a = m.given[0]
    edge = m.given[2] if m.kind == "oblique_rhombus" else m.given[1]
    angle = m.given[-1]
    rows = (
        "<p>"
        + picture
        + "Объём призмы или параллелепипеда равен произведению площади основания на перпендикулярную высоту. Боковое ребро L наклонено к основанию под углом α:</p>"
        + line("V=BH")
        + line(r"H=L\sin\alpha")
        + line(
            "H="
            + bracket(edge)
            + r"\sin "
            + value(angle)
            + r"^\circ="
            + value(m.height)
        )
    )
    if m.kind == "oblique_rhombus":
        rows += (
            "<p>Основание — ромб со стороной a и углом β. Найдём его площадь:</p>"
            + line(r"B=a^2\sin\beta")
            + line(
                "B="
                + bracket(a)
                + r"^2\sin "
                + value(m.given[1])
                + r"^\circ="
                + value(m.area)
            )
        )
    else:
        rows += (
            "<p>Основание — правильный шестиугольник. Найдём его площадь:</p>"
            + line(r"B=\frac{3\sqrt{3}}{2}a^2")
            + line(r"B=\frac{3\sqrt{3}}{2}\cdot" + bracket(a) + "^2=" + value(m.area))
        )
    return (
        rows
        + "<p>Подставим площадь основания и найденную высоту:</p>"
        + line("V=" + bracket(m.area) + r"\cdot" + bracket(m.height))
        + line("V=" + value(m.answer))
    )
