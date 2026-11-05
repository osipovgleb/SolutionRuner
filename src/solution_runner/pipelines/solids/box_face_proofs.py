"""Retain the shared face-area times perpendicular-edge method."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def render(m):
    v, h = m.given
    common = (
        "<p>Объём прямоугольного параллелепипеда равен произведению площади грани S и длины перпендикулярного ей ребра h:</p>"
        + line("V=Sh")
    )
    if m.mode == "volume_from_face":
        return (
            common
            + "<p>По условию известны площадь грани и перпендикулярное ребро:</p>"
            + line("S=" + value(v))
            + line("h=" + value(h))
            + "<p>Подставим значения и найдём объём:</p>"
            + line("V=" + bracket(v) + r"\cdot" + bracket(h))
            + line("V=" + value(m.answer))
        )
    symbol, denominator = ("S", "h") if m.mode == "face_from_volume" else ("h", "S")
    return (
        common
        + "<p>По условию известны:</p>"
        + line("V=" + value(v))
        + line(denominator + "=" + value(h))
        + "<p>Выразим искомую величину и подставим данные:</p>"
        + line(symbol + r"=\frac{V}{" + denominator + "}")
        + line(symbol + r"=\frac{" + value(v) + "}{" + value(h) + "}")
        + line(symbol + "=" + value(m.answer))
    )
