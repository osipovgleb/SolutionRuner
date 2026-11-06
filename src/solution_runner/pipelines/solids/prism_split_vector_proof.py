"""Keep the coordinate method and the parent's scalar-triple-product ending."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _tuple(values):
    return "(" + ";".join(sp.latex(v) for v in values) + ")"


def _claim(m):
    quarter = m.names[0] == "quarter"
    vector = (
        r"\frac14(\vec{a}+\vec{b})-\vec{c}" if quarter else r"\frac12\vec{b}-\vec{c}"
    )
    proof = (
        "<p>Положим a⃗ = BA⃗, b⃗ = BC⃗, c⃗ = BB₁⃗. Из AB = BC следует равенство длин векторов a⃗ и b⃗. Призма прямая, поэтому c⃗ перпендикулярен обоим этим векторам.</p>"
        + line(r"\overrightarrow{KM}=" + vector)
    )
    if quarter:
        return (
            proof
            + line(r"\overrightarrow{AC}=\vec{b}-\vec{a}")
            + line(r"\overrightarrow{KM}\cdot\overrightarrow{AC}=\frac14(BC^2-AB^2)=0")
            + "<p>Следовательно, KM ⟂ AC.</p>"
        )
    return (
        proof
        + line(r"\overrightarrow{KB}=-\frac12\vec{a}-\vec{c}")
        + line(r"KM^2=\frac14BC^2+BB_1^2=\frac14AB^2+BB_1^2=KB^2")
        + "<p>Таким образом, KM = KB.</p>"
    )


def _coordinates(m):
    q = m.q
    b, v, h, t = (q[k] for k in ("b", "base_height", "height", "fraction"))
    km = (b * (t - sp.Rational(1, 4)), -v / 2, -h)
    return (
        "<p>Пусть α — угол между KM и ABB₁. Поместим начало координат в A, ось x направим по AC, ось z — вдоль бокового ребра. Точка B имеет положительную ординату:</p>"
        + line(
            "A(0;0;0),\\quad C"
            + _tuple((b, 0, 0))
            + r",\quad B"
            + _tuple((b / 2, v, 0))
        )
        + line("K" + _tuple((b / 4, v / 2, h)) + r",\quad M" + _tuple((t * b, 0, 0)))
        + line(r"\overrightarrow{KM}=" + _tuple(km))
        + line(
            r"|\overrightarrow{KM}|=\sqrt{"
            + "+".join(bracket(x) + "^2" for x in km)
            + "}="
            + value(q["KM"])
        )
        + line(
            r"\overrightarrow{AB}="
            + _tuple((b / 2, v, 0))
            + r",\qquad \overrightarrow{BB_1}="
            + _tuple((0, 0, h))
        )
        + "<p>Векторное произведение двух направляющих векторов плоскости даёт нормаль. Поскольку h &gt; 0, можно сократить общий множитель h:</p>"
        + line(
            r"\overrightarrow{AB}\times\overrightarrow{BB_1}="
            + _tuple((h * v, -h * b / 2, 0))
        )
        + line(r"\vec{n}=" + _tuple((v, -b / 2, 0)))
        + line(
            r"|\vec{n}|=\sqrt{"
            + bracket(v)
            + "^2+"
            + bracket(b / 2)
            + "^2}="
            + value(q["normal_norm"])
        )
        + line(
            r"\overrightarrow{KM}\cdot\vec{n}="
            + bracket(km[0])
            + r"\cdot "
            + bracket(v)
            + "+"
            + bracket(km[1])
            + r"\cdot "
            + bracket(-b / 2)
            + "="
            + value(q["normal_dot"])
        )
        + line(
            r"\sin\alpha=\frac{|\overrightarrow{KM}\cdot\vec{n}|}{|\overrightarrow{KM}|\cdot|\vec{n}|}=\frac{"
            + bracket(q["normal_dot"])
            + "}{"
            + bracket(q["KM"])
            + r"\cdot "
            + bracket(q["normal_norm"])
            + "}="
            + value(q["sine"])
        )
    )


def _triple_product(m):
    q = m.q
    a, b, h, t = (q[k] for k in ("a", "b", "height", "fraction"))
    cos_beta, sin_beta = (
        sp.simplify(1 - b * b / (2 * a * a)),
        sp.simplify(b * q["base_height"] / (a * a)),
    )
    normal_norm, numerator = a * h, sp.simplify(t * a * a * h * sin_beta)
    return (
        "<p><b>Замечание. Можно обойтись только векторами, без координат.</b> Возьмём нормаль n⃗₀ = a⃗ × c⃗. Векторы a⃗ и c⃗ перпендикулярны, поэтому:</p>"
        + line(r"\vec{n}_0=\vec{a}\times\vec{c}")
        + line(
            r"|\vec{n}_0|=AB\cdot BB_1="
            + bracket(a)
            + r"\cdot "
            + bracket(h)
            + "="
            + value(normal_norm)
        )
        + "<p>В скалярном произведении KM⃗ с нормалью слагаемые, содержащие a⃗ и c⃗, равны нулю. Остаётся слагаемое с b⃗. Переставим множители смешанного произведения; b⃗ × a⃗ параллелен c⃗:</p>"
        + line(
            r"|\overrightarrow{KM}\cdot\vec{n}_0|="
            + sp.latex(t)
            + r"|\vec{b}\cdot(\vec{a}\times\vec{c})|="
            + sp.latex(t)
            + r"|\vec{b}\times\vec{a}|\cdot|\vec{c}|"
        )
        + "<p>Найдём синус угла ABC через теорему косинусов:</p>"
        + line(r"\cos\angle ABC=\frac{AB^2+BC^2-AC^2}{2AB\cdot BC}=" + value(cos_beta))
        + line(
            r"\sin\angle ABC=\sqrt{1-" + bracket(cos_beta) + "^2}=" + value(sin_beta)
        )
        + line(
            r"|\overrightarrow{KM}\cdot\vec{n}_0|="
            + sp.latex(t)
            + r"AB\cdot BC\cdot BB_1\sin\angle ABC="
            + value(numerator)
        )
        + _norm(m)
        + line(
            r"\sin\alpha=\frac{|\overrightarrow{KM}\cdot\vec{n}_0|}{|\overrightarrow{KM}|\cdot|\vec{n}_0|}=\frac{"
            + bracket(numerator)
            + "}{"
            + bracket(q["KM"])
            + r"\cdot "
            + bracket(normal_norm)
            + "}="
            + value(q["sine"])
        )
    )


def _norm(m):
    q = m.q
    if m.names[0] == "half":
        formula = r"|\overrightarrow{KM}|^2=\frac14|\vec{b}|^2+|\vec{c}|^2="
    else:
        formula = r"|\overrightarrow{KM}|^2=\frac1{16}|\vec{a}|^2+\frac1{16}|\vec{b}|^2+\frac18\vec{a}\cdot\vec{b}+|\vec{c}|^2="
    return (
        "<p>Осталось найти длину KM⃗. Скалярное произведение a⃗ и b⃗ выразим через стороны основания, затем раскроем квадрат длины суммы векторов:</p>"
        + line(r"\vec{a}\cdot\vec{b}=\frac{AB^2+BC^2-AC^2}{2}=" + value(q["base_dot"]))
        + line(formula + value(q["KM"] ** 2))
        + line(r"|\overrightarrow{KM}|=" + value(q["KM"]))
    )


def render(m, pictures):
    return (
        "<p><b>Решение векторами и координатами.</b></p>"
        + parts(
            _claim(m) + pictures.get("image_2", "") + pictures.get("image_3", ""),
            _coordinates(m),
        )
        + pictures.get("image_2", "")
        + _triple_product(m)
    )
