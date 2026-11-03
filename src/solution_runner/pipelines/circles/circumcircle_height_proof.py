"""Keep the parent's two right triangles and its sum-versus-difference note."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def render(m, pictures):
    large, small, radius, inside = m.given
    ko = sp.sqrt(radius**2 - small**2 / 4)
    oh = sp.sqrt(radius**2 - large**2 / 4)
    operation = "+" if inside else "-"
    location = (
        "между основаниями"
        if inside
        else "вне трапеции, по одну сторону от обоих оснований"
    )
    return (
        "<p>"
        + pictures["height"]
        + "Высота трапеции KH. Перпендикуляры из центра O к основаниям делят основания пополам; KO и OH — высоты равнобедренных треугольников DOC и AOB. Центр лежит "
        + location
        + ", поэтому:</p>"
        + line("KH=KO" + operation + "OH")
        + "<p>По теореме Пифагора найдём оба расстояния от центра до оснований:</p>"
        + line(r"KO=\sqrt{OC^2-KC^2}=\sqrt{R^2-\frac{DC^2}{4}}")
        + line(
            r"KO=\sqrt{"
            + bracket(radius)
            + r"^2-\frac{"
            + bracket(small)
            + "^2}{4}}="
            + value(ko)
        )
        + line(r"OH=\sqrt{OB^2-HB^2}=\sqrt{R^2-\frac{AB^2}{4}}")
        + line(
            r"OH=\sqrt{"
            + bracket(radius)
            + r"^2-\frac{"
            + bracket(large)
            + "^2}{4}}="
            + value(oh)
        )
        + "<p>Тогда высота равна:</p>"
        + line(
            "KH=KO"
            + operation
            + "OH="
            + bracket(ko)
            + operation
            + bracket(oh)
            + "="
            + value(m.answer)
        )
        + "<p><b>Примечание.</b></p><p>Если оба основания расположены по одну сторону от центра окружности, длина высоты равна разности найденных расстояний. Если центр лежит внутри трапеции, высота равна их сумме.</p>"
    )
