"""Retain the existing child's coordinate addendum when its reviewed scene is present."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def render(m, pictures):
    q = m.q
    a, h, e = q["a"], q["height"], q["AE"]
    top = q["A1E"]
    return (
        pictures["image_2"]
        + "<p><b>Другой способ. Метод координат.</b> Начало координат выберем в B, оси направим вдоль BC, BA и BB₁. Тогда:</p>"
        + line(
            r"A(0;" + value(a) + r";0),\quad B(0;0;0),\quad C(" + value(a) + r";0;0)"
        )
        + line(
            r"D_1("
            + value(a)
            + ";"
            + value(a)
            + ";"
            + value(h)
            + r"),\quad E(0;"
            + value(a)
            + ";"
            + value(e)
            + ")"
        )
        + "<p>Плоскость BED₁ проходит через начало координат, поэтому её уравнение имеет вид Nₓx + Nᵧy + N𝓏z = 0. Подставим E и D₁:</p>"
        + line(
            r"\begin{cases}"
            + value(a)
            + "N_y+"
            + value(e)
            + r"N_z=0\\"
            + value(a)
            + "N_x+"
            + value(a)
            + "N_y+"
            + value(h)
            + r"N_z=0\end{cases}"
        )
        + "<p>Выберем ненулевой множитель нормали так, чтобы N𝓏 = −AB. Из первого уравнения найдём Nᵧ, а из разности второго и первого — Nₓ:</p>"
        + line(
            r"N_z=-"
            + value(a)
            + r",\qquad N_y="
            + value(e)
            + r",\qquad N_x="
            + value(h)
            + "-"
            + value(e)
            + "="
            + value(top)
        )
        + line(
            r"\vec n_{BED_1}=("
            + value(top)
            + ";"
            + value(e)
            + ";-"
            + value(a)
            + r"),\qquad \vec n_{ABC}=(0;0;1)"
        )
        + "<p>Возьмём модуль косинуса угла между нормалями:</p>"
        + line(
            r"\cos\varphi=\frac{"
            + value(a)
            + r"}{\sqrt{"
            + bracket(top)
            + "^2+"
            + bracket(e)
            + "^2+"
            + bracket(a)
            + "^2}}="
            + value(a / sp.sqrt(top * top + e * e + a * a))
        )
        + line(
            r"\tan\varphi=\frac{\sqrt{1-\cos^2\varphi}}{\cos\varphi}=" + value(q["tan"])
        )
    )
