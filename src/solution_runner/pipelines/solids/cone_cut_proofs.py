"""Keep the parents' angular-fraction method with the cone volume factor one third."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .measurements import sector_fraction


def render(m):
    radius, height, angle = m.given
    fraction = sector_fraction(angle, m.kind)
    kept = angle if m.kind == "kept" else 360 - angle
    rows = "<p>Объём данной части конуса составляет такую же долю объёма полного конуса, какую её центральный угол составляет от полного угла:</p>"
    rows += (
        line(r"\alpha=" + value(kept) + r"^\circ")
        if m.kind == "kept"
        else line(
            r"\alpha=360^\circ-" + value(angle) + r"^\circ=" + value(kept) + r"^\circ"
        )
    )
    return (
        rows
        + line(
            r"k=\frac{\alpha}{360^\circ}=\frac{"
            + value(kept)
            + "}{360}="
            + value(fraction)
        )
        + "<p>Полный объём конуса равен трети произведения площади основания на высоту. Умножим его на найденную долю:</p>"
        + line(r"V_{\mathrm{кон}}=\frac{1}{3}\pi r^2h")
        + line(r"V=kV_{\mathrm{кон}}=k\cdot\frac{1}{3}\pi r^2h")
        + line(
            "V="
            + bracket(fraction)
            + r"\cdot\frac{1}{3}\cdot\pi\cdot"
            + bracket(radius)
            + r"^2\cdot"
            + bracket(height)
        )
        + line("V=" + value(sp.pi * m.answer))
        + "<p>В ответе требуется объём, делённый на π:</p>"
        + line(
            r"\frac{V}{\pi}=\frac{"
            + value(sp.pi * m.answer)
            + r"}{\pi}="
            + value(m.answer)
        )
    )
