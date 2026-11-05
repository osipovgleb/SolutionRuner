"""Retain the parent's second method with corrected axes and normal equations."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def render(m, pictures):
    q = m.q
    r, t = q["r"], q["top"]
    inverse = m.mode.endswith("height")
    normal = r"\vec n_{\beta}" if inverse else r"\vec n_{\alpha}"
    first = (
        "<p><b>Другой способ. Метод координат.</b></p>"
        + pictures.get("image_2", "")
        + "<p>Начало координат выберем в A, ось y направим вдоль AC, ось x — в плоскости основания перпендикулярно AC в сторону B, ось z — вдоль AA₁. Пусть a = AB, b = AA₁. Тогда:</p>"
        + (
            "<p>Обозначим середину A₁B₁ через K. Построим вспомогательную плоскость β через M и K перпендикулярно грани ABB₁A₁. Её совпадение с заданной α докажем после проверки C₁.</p>"
            if inverse
            else ""
        )
        + line(r"A(0;0;0),\quad B(\frac{a\sqrt3}{2};\frac a2;0),\quad C_1(0;a;b)")
        + line(r"M(0;0;" + value(r) + r"b),\quad K(\frac{a\sqrt3}{4};\frac a4;b)")
        + "<p>Грань ABB₁A₁ лежит в плоскости x − √3y = 0 с нормалью (1; −√3; 0). Для компонент нормали рассматриваемой плоскости и её свободного члена d записываем принадлежность M, K и перпендикулярность нормалей. Решая систему, можно выбрать следующую нормаль и уравнение:</p>"
        + line(
            r"\begin{cases}"
            + value(r)
            + r"bN_z+d=0\\\frac{a\sqrt3}{4}N_x+\frac a4N_y+bN_z+d=0\\N_x-\sqrt3N_y=0\end{cases}"
        )
        + line(r"N_x=\sqrt3 N_y")
        + line("d=-" + value(r) + r"b N_z")
        + line("a N_y+" + value(t) + r"b N_z=0")
        + "<p>Нормаль определена с точностью до ненулевого множителя. Выберем удобный множитель:</p>"
        + line("N_y=" + value(t) + "b")
        + line("N_z=-a")
        + line("d=" + value(r) + "ab")
        + line(normal + "=(" + value(t) + r"\sqrt3 b;" + value(t) + "b;-a)")
        + line(value(t) + r"\sqrt3 bx+" + value(t) + "by-az+" + value(r) + "ab=0")
        + "<p>Скалярное произведение нормалей равно нулю. Координаты M и K удовлетворяют уравнению. Проверим C₁:</p>"
        + line(value(t) + "ab-ab+" + value(r) + "ab=0")
        + (
            "<p>Значит, β содержит C₁ и M и перпендикулярна грани ABB₁A₁. Обе плоскости α и β содержат перпендикуляр к этой грани, проведённый через C₁, и не лежащую на нём точку M. Поэтому β совпадает с α. Следовательно, K принадлежит α и является серединой A₁B₁.</p>"
            if m.mode.endswith("height")
            else "<p>Значит, C₁ лежит в плоскости α.</p>"
        )
    )
    a = q["a"]
    cross = (3 * t * a * a / 4, sp.sqrt(3) * t * a * a / 4, -sp.sqrt(3) * a * a / 4)
    second = (
        "<p>При равных рёбрах a = b. Найдём площадь треугольника с помощью векторного произведения:</p>"
        + line(
            r"\overrightarrow{C_1K}=(\frac{a\sqrt3}{4};-\frac{3a}{4};0),\quad \overrightarrow{C_1M}=(0;-a;-"
            + value(t)
            + "a)"
        )
        + line(
            r"\left|\overrightarrow{C_1K}\times\overrightarrow{C_1M}\right|=\frac{\sqrt3}{2}a^2\sqrt{"
            + bracket(t)
            + r"^2+\frac14}"
        )
        + line(r"S_{MKC_1}=\frac{\sqrt3}{4}a^2\sqrt{" + bracket(t) + r"^2+\frac14}")
    )
    if m.mode.endswith("height"):
        second += line(
            r"a^2=\frac{4\cdot "
            + bracket(q["area"])
            + r"}{\sqrt3\sqrt{"
            + bracket(t)
            + r"^2+\frac14}}="
            + value(a * a)
        ) + line(r"AA_1=a=" + value(a))
    else:
        second += (
            line("a=" + value(a))
            + line(
                r"\overrightarrow{C_1K}\times\overrightarrow{C_1M}=("
                + ";".join(value(v) for v in cross)
                + ")"
            )
            + line(
                r"S_{MKC_1}=\frac12\sqrt{"
                + "+".join(bracket(v) + "^2" for v in cross)
                + "}="
                + value(m.answer)
            )
        )
    return parts(first, second)
