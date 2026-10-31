"""Render all three verified notes after the interval selection, in source order."""

import sympy as sp

from ..probability.common import line

X = sp.Symbol("x", real=True)


def notes(a):
    return squared(a) + product(a) + cosine(a)


def squared(a):
    from .exam_trigonometric_proof import pi, series_lines

    _tau, square, parity, _ = a.four_methods
    t = sp.Symbol("t", real=True)
    z = next(iter(square.free_symbols))
    polynomial = -square.subs(z, t)
    html = "<p><b>Примечание 1.</b> Можно обозначить синус двойного угла после возведения уравнения в квадрат. При этом обязательно проверим найденные корни в исходном уравнении.</p>"
    html += line(r"\sin^2 2x(\sin x-\cos x)^2=2")
    html += line(r"\sin^2 2x(1-\sin 2x)=2")
    html += line(r"t=\sin 2x") + line(sp.latex(polynomial) + "=0")
    html += line(sp.latex(sp.factor(polynomial)) + "=0")
    html += line(r"D=(-2)^2-4\cdot1\cdot2=-4<0")
    html += line("t=-1") + line(r"\sin 2x=-1")
    html += line(
        series_lines(((-sp.Rational(1, 4), sp.S.One),))[0] + r",\quad k\in\mathbb Z"
    )
    html += "<p>Подставим серии с чётными и нечётными индексами. Периодичность синуса и косинуса делает проверку верной для каждого целого m:</p>"
    for r in (0, 1):
        value = sp.sqrt(2) * (-1) ** r
        html += line("k=2m" + ("" if r == 0 else "+1"))
        html += line("x=" + pi(-sp.Rational(1, 4) + r) + r"+2\pi m")
        html += line(r"\sin 2x(\sin x-\cos x)=" + sp.latex(value))
        html += (
            "<p>Это равно правой части; вся серия подходит.</p>"
            if r == parity
            else "<p>Это не равно правой части исходного уравнения; вся серия посторонняя.</p>"
        )
    return html


def product(a):
    from .exam_trigonometric_proof import families, pi

    tau, _, _, _ = a.four_methods
    html = "<p>Следующие два решения используют ограниченность тригонометрических функций.</p><p><b>Приведём другое решение пункта а).</b></p>"
    html += line(r"\sin 2x\sin\left(x-\frac{\pi}{4}\right)=" + sp.latex(tau))
    html += "<p>Модуль каждого множителя не превосходит 1. Произведение равно указанному предельному значению только в двух случаях:</p>"
    for sign in (-1, 1):
        q = sp.Rational(1, 4) + tau * sign / 2
        actual = sp.simplify(sp.sin(2 * sp.pi * q))
        html += line(
            r"\begin{cases}\sin 2x="
            + str(sign)
            + r"\\\sin\left(x-\frac{\pi}{4}\right)="
            + str(tau * sign)
            + r"\end{cases}"
        )
        html += line("x=" + pi(q) + r"+2\pi k,\quad k\in\mathbb Z")
        html += line(
            r"\sin 2x=\sin\left(" + pi(2 * q) + r"+4\pi k\right)=" + sp.latex(actual)
        )
        html += (
            "<p>Оба условия выполнены для каждого целого k.</p>"
            if actual == sign
            else "<p>Полученное значение противоречит первому условию. Эта система несовместна.</p>"
        )
    html += "<p>Поэтому остаётся единственная серия:</p>"
    for text in families(a):
        html += line(text + r",\quad k\in\mathbb Z")
    return html


def cosine(a):
    from .exam_trigonometric_proof import series_lines

    tau, _, _, index = a.four_methods
    q = -sp.Rational(1, 4) + (1 if tau == -1 else 0)
    beta = 1 if tau == 1 else 0
    other = (sp.Rational(beta) + sp.Rational(1, 4)) / 3
    html = "<p><b>Приведём ещё одно решение уравнения, использующее ограниченность функций.</b></p>"
    html += line(r"2\sin 2x\sin\left(x-\frac{\pi}{4}\right)=2\cdot(" + str(tau) + ")")
    html += line(
        r"\cos\left(x+\frac{\pi}{4}\right)-\cos\left(3x-\frac{\pi}{4}\right)="
        + str(2 * tau)
    )
    html += "<p>Разность достигает своей границы только при одновременном выполнении двух условий:</p>"
    html += line(
        r"\begin{cases}\cos\left(x+\frac{\pi}{4}\right)="
        + str(tau)
        + r"\\\cos\left(3x-\frac{\pi}{4}\right)="
        + str(-tau)
        + r"\end{cases}"
    )
    html += line(series_lines(((q, sp.Integer(2)),))[0] + r",\quad k\in\mathbb Z")
    html += line(
        series_lines(((other, sp.Rational(2, 3)),))[0].replace("k", "n")
        + r",\quad n\in\mathbb Z"
    )
    k = sp.Symbol("k", integer=True)
    n = sp.Symbol("n", integer=True)
    html += line(
        sp.latex((q + 2 * k) * sp.pi)
        + "="
        + sp.latex((other + sp.Rational(2, 3) * n) * sp.pi)
    )
    html += line("n=" + sp.latex(index) + r"\in\mathbb Z")
    html += "<p>Каждому целому k соответствует целый n. Значит, вся первая серия и только она удовлетворяет системе.</p>"
    return html
