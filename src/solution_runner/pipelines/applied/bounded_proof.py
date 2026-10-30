"""Reciprocal lens reasoning and the parent's below-resonance percentage note."""

import sympy as sp

from ..calculus.common import answer
from ..probability.common import line
from .fraction_questions import X


def final(label, result, unit):
    decimal = answer(result).replace(",", "{,}")
    return line(
        label
        + "="
        + sp.latex(result)
        + ("=" + decimal if result.is_Integer is not True else "")
        + r"\ "
        + unit
    )


def lens(a):
    q = a.question
    v = q.values
    f = v["focus"]
    screen = q.expression.subs(X, a.result)
    reciprocal = 1 / a.result
    html = "<p>Из формулы линзы выразим величину, обратную расстоянию до лампочки:</p>"
    html += line(r"\frac1{d_1}+\frac1{d_2}=\frac1f")
    html += line(r"\frac1{d_1}=\frac1{" + sp.latex(f) + r"}-\frac1{d_2}")
    html += "<p>Наименьшему положительному расстоянию до лампочки соответствует наибольшая обратная величина. Правая часть возрастает при увеличении расстояния до экрана.</p>"
    if screen == v["far_max"]:
        html += "<p>Возьмём наибольшее разрешённое расстояние до экрана, затем проверим диапазон расстояний до лампочки:</p>"
    else:
        html += line(r"d_1\in" + sp.latex(a.feasible))
        html += "<p>Заданный нижний предел расстояния до лампочки ограничивает выбор сильнее, чем верхний предел расстояния до экрана. Соответствующее расстояние до экрана равно:</p>"
    html += line(r"d_2=" + sp.latex(screen))
    html += line(
        r"\frac1{d_1}=\frac1{" + sp.latex(f) + r"}-\frac1{" + sp.latex(screen) + "}"
    )
    html += line(r"\frac1{d_1}=" + sp.latex(reciprocal))
    html += line(
        sp.latex(v["near_min"])
        + r"\leq d_1\leq"
        + sp.latex(v["near_max"])
        + r",\quad "
        + sp.latex(v["far_min"])
        + r"\leq d_2\leq"
        + sp.latex(v["far_max"])
    )
    html += "<p>Найденные расстояния входят в оба заданных диапазона; нижняя граница допустима.</p>"
    return html + final(r"{d_1}_{\min}", a.result, r"\text{см}")


def resonance(a):
    q = a.question
    v = q.values
    f, p = v["resonant"], v["target"]
    ratio = f**2 * p / (100 + p)
    html = "<p>Частота неотрицательна и меньше резонансной. Поэтому выражение под модулем положительно:</p>"
    html += line(
        r"0\leq\omega<"
        + sp.latex(f)
        + r",\quad |\omega_p^2-\omega^2|=\omega_p^2-\omega^2"
    )
    html += "<p>Исходная амплитуда положительна. Условие об относительном увеличении амплитуды означает:</p>"
    html += line(
        r"A\leq A_0\left(1+\frac{"
        + sp.latex(p)
        + r"}{100}\right)="
        + sp.latex(q.target)
        + r"A_0"
    )
    html += line(
        r"\frac{A_0\cdot"
        + sp.latex(f)
        + r"^2}{"
        + sp.latex(f)
        + r"^2-\omega^2}\leq"
        + sp.latex(q.target)
        + "A_0"
    )
    html += line(
        sp.latex(f**2)
        + r"\leq"
        + sp.latex(q.target)
        + r"\left("
        + sp.latex(f**2)
        + r"-\omega^2\right)"
    )
    html += line(sp.latex(q.target) + r"\omega^2\leq" + sp.latex((q.target - 1) * f**2))
    html += line(r"\omega^2\leq" + sp.latex(ratio))
    html += line(r"0\leq\omega\leq\sqrt{" + sp.latex(ratio) + "}=" + sp.latex(a.result))
    html += "<p>Полученная граница меньше резонансной частоты и допускается нестрогим неравенством.</p>"
    html += final(r"\omega_{\max}", a.result, r"\mathrm{с}^{-1}")
    html += "<p>Примечание. Процентное увеличение относится к исходной амплитуде, поэтому:</p>"
    html += line(
        sp.latex(p)
        + r"\%=\frac{"
        + sp.latex(p)
        + "}{100}="
        + sp.latex(p / 100)
        + r",\quad A_0+"
        + sp.latex(p / 100)
        + r"A_0="
        + sp.latex(q.target)
        + r"A_0"
    )
    return html
