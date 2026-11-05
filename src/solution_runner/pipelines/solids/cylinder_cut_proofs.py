"""Retain the parents' sector, sum and difference methods with explicit π units."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def _quotient(m):
    return "<p>В ответе требуется объём, делённый на π:</p>" + line(
        r"\frac{V}{\pi}=\frac{" + value(sp.pi * m.answer) + r"}{\pi}=" + value(m.answer)
    )


def sector(m):
    radius, height, angle = m.given
    kept = angle if m.kind == "kept" else 360 - angle
    fraction = sp.Rational(kept, 360)
    rows = "<p>Объём данной части цилиндра составляет такую же долю объёма полного цилиндра, какую её центральный угол составляет от полного угла:</p>"
    if m.kind == "removed":
        rows += line(
            r"\alpha=360^\circ-" + value(angle) + r"^\circ=" + value(kept) + r"^\circ"
        )
    else:
        rows += line(r"\alpha=" + value(kept) + r"^\circ")
    return (
        rows
        + line(
            r"k=\frac{\alpha}{360^\circ}=\frac{"
            + value(kept)
            + "}{360}="
            + value(fraction)
        )
        + "<p>Для полного цилиндра используем радиус основания и высоту с рисунка:</p>"
        + line(r"V_{\mathrm{цил}}=\pi r^2h")
        + line(r"V=k\pi r^2h")
        + line(
            "V="
            + bracket(fraction)
            + r"\cdot\pi\cdot"
            + bracket(radius)
            + r"^2\cdot"
            + bracket(height)
        )
        + line("V=" + value(sp.pi * m.answer))
        + _quotient(m)
    )


def stepped(m):
    radius, total, base = m.given
    extra = total - base
    return (
        "<p>Объём данной фигуры равен сумме объёмов нижнего цилиндра и половины цилиндра над ним. На рисунке указаны полная высота H и высота нижней части h₁; найдём высоту верхней части:</p>"
        + line("h_2=H-h_1")
        + line("h_2=" + value(total) + "-" + value(base) + "=" + value(extra))
        + "<p>Обе части имеют одинаковый радиус основания. Сложим их объёмы:</p>"
        + line(r"V_1=\pi r^2h_1")
        + line(r"V_2=\frac{1}{2}\pi r^2h_2")
        + line(r"V=V_1+V_2=\pi r^2\left(h_1+\frac{h_2}{2}\right)")
        + line(
            r"V=\pi\cdot"
            + bracket(radius)
            + r"^2\left("
            + value(base)
            + r"+\frac{"
            + value(extra)
            + r"}{2}\right)"
        )
        + line("V=" + value(sp.pi * m.answer))
        + _quotient(m)
    )


def annular(m):
    outer, inner, height = m.given
    return (
        "<p>Объём данной фигуры равен разности объёмов внешнего цилиндра и цилиндрического отверстия. Их высоты одинаковы:</p>"
        + line(r"V_1=\pi R^2H")
        + line(r"V_2=\pi r^2H")
        + "<p>Вычтем объём отверстия и подставим размеры с рисунка:</p>"
        + line(r"V=V_1-V_2=\pi H(R^2-r^2)")
        + line(
            r"V=\pi\cdot"
            + bracket(height)
            + r"\left("
            + bracket(outer)
            + "^2-"
            + bracket(inner)
            + r"^2\right)"
        )
        + line(
            r"V=\pi\cdot"
            + bracket(height)
            + r"\left("
            + value(outer**2)
            + "-"
            + value(inner**2)
            + r"\right)"
        )
        + line("V=" + value(sp.pi * m.answer))
        + _quotient(m)
    )
