"""Retain each original log identity and its substitution/back-substitution order."""

from functools import cmp_to_key

import sympy as sp

from ..probability.common import line
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_log_identity import Z
from .exam_trigonometric_log_product import conditions
from .exam_trigonometric_log_product_proof import rejections
from .exam_trigonometric_radical_product import factor_branches


def log(base, argument):
    return r"\log_{" + base + r"}\left(" + argument + r"\right)"


def domain(a):
    from .exam_trigonometric_proof import formula

    d = a.log_product.equality.identity
    names = {
        value: text
        for atom, texts in zip(d.atoms, d.texts, strict=True)
        for value, text in zip((atom.base, atom.argument), texts, strict=True)
    }
    html = "<p>Сохраним ограничения всех исходных логарифмов и знаменателей до сокращений:</p>"
    for p, relation in conditions(a):
        if not p.free_symbols:
            continue
        html += line(
            names.get(p, formula(p)) + (">0" if relation == "positive" else r"\ne0")
        )
    return html


def series(variable, value, allow_inverse):
    from .exam_trigonometric_inverse import level_series
    from .exam_trigonometric_proof import series_lines

    return "".join(
        line(f + r",\quad k\in\mathbb Z")
        for f in series_lines(level_series(variable, value, allow_inverse))
    )


def power_steps(a):
    from .exam_trigonometric_proof import formula

    d = a.log_product.equality.identity
    html = "<p>Применим формулу приведения в левой части:</p>"
    for text, value in dict.fromkeys(a.identities):
        if text not in (r"\sin(x)", r"\cos(x)"):
            html += line(text + "=" + formula(value))
    html += domain(a)
    html += "<p>На исходной области определения логарифм степени своего основания равен показателю:</p>"
    html += line(log(*d.texts[0]) + "=" + sp.latex(d.log_value))
    variable = next(iter(d.converted.free_symbols))
    html += "<p>Решим квадратное уравнение относительно обратной тригонометрической функции:</p>"
    html += line(
        sp.latex(
            d.polynomial,
            symbol_names={Z: r"\left(\frac{1}{" + formula(variable) + r"}\right)"},
        )
        + "=0"
    )
    for value in sorted(roots(d.polynomial.subs(Z, X)), key=cmp_to_key(compare)):
        html += line(r"\frac{1}{" + formula(variable) + "}=" + sp.latex(value))
        if value == 0:
            html += "<p>Обратная величина не может быть равна нулю.</p>"
            continue
        level = sp.cancel(1 / value)
        html += line(formula(variable) + "=" + sp.latex(level))
        if -1 <= level <= 1:
            html += series(variable, level, a.allow_inverse)
        else:
            html += "<p>Это значение не входит в отрезок от −1 до 1.</p>"
    return html


def chain_steps(a):
    from .exam_trigonometric_proof import candidate_lines

    d = a.log_product.equality.identity
    html = domain(a) + "<p>При допустимых значениях применим тождество:</p>"
    html += line(r"\log_a b\cdot\log_b c=\log_a c")
    base = d.texts[0][0]
    argument = d.texts[1][1]
    html += line(log(base, argument) + "=" + sp.latex(d.level))
    target = sp.simplify(d.atoms[0].base ** d.level)
    html += line(argument + "=" + sp.latex(target))
    for b in factor_branches(a.raw, S, a.allow_inverse):
        html += candidate_lines(b, allow_inverse=a.allow_inverse)
    return html


def substitution(a):

    d = a.log_product.equality.identity
    t = d.substitution
    if d.kind == "base_product":
        first, second = (texts[1] for texts in d.texts)
        html = line(d.texts[0][0] + "=" + first + r"\cdot" + second)
        html += "<p>Из положительности обоих аргументов и основного тригонометрического тождества следует, что каждый из них меньше единицы. Поэтому можно перейти к этим основаниям:</p>"
        html += line("0<" + first + "<1") + line("0<" + second + "<1")
        html += line(log(*d.texts[0]) + r"=\frac{1}{1+" + log(first, second) + "}")
        html += line(log(*d.texts[1]) + r"=\frac{1}{1+" + log(second, first) + "}")
    else:
        first, second = d.texts[0]
        html = ""
    html += "<p>Сделаем замену, сохраняя условия существования обратного логарифма:</p>"
    html += line(t + "=" + log(first, second))
    html += line(second + r"\ne1\quad\Longrightarrow\quad " + t + r"\ne0")
    html += line(log(second, first) + r"=\frac{1}{" + t + "}")
    if d.kind == "base_product":
        html += line(t + ">0")
        html += line(
            r"\frac{1}{1+"
            + t
            + r"}\cdot\frac{1}{1+\frac{1}{"
            + t
            + r"}}=\frac{"
            + t
            + "}{(1+"
            + t
            + ")^2}="
            + sp.latex(d.level)
        )
        html += line(t + r"\ne-1")
    else:
        html += line(t + r"+\frac{1}{" + t + "}=" + sp.latex(d.level))
    html += "<p>Умножим на ненулевые знаменатели и решим квадратное уравнение:</p>"
    p = sp.Poly(d.polynomial, Z).clear_denoms()[1].primitive()[1].as_expr()
    html += line(sp.latex(p, symbol_names={Z: t}) + "=0")
    html += line(sp.latex(sp.factor(p), symbol_names={Z: t}) + "=0")
    html += line(t + "=" + sp.latex(d.log_value))
    return html, first, second


def back_substitution(a, first, second):
    from .exam_trigonometric_proof import formula, polynomial

    d = a.log_product.equality.identity
    html = "<p>Вернёмся к исходной переменной:</p>"
    html += line(log(first, second) + "=" + sp.latex(d.log_value))
    html += line(
        second + "=" + first if d.log_value == 1 else second + r"\cdot" + first + "=1"
    )
    if d.kind == "base_product":
        from .exam_trigonometric_compile import T
        from .exam_trigonometric_inverse import level_series
        from .exam_trigonometric_proof import series_lines

        html += line(r"\sin x=\cos x")
        html += (
            "<p>Оба исходных аргумента положительны, поэтому косинус не равен нулю:</p>"
        )
        html += line(r"\cos x\ne0") + line(r"\tg x=1")
        html += "".join(
            line(f + r",\quad k\in\mathbb Z")
            for f in series_lines(level_series(T, sp.S.One, a.allow_inverse))
        )
        return html
    for text, value in dict.fromkeys(a.identities):
        if text not in (r"\sin(x)", r"\cos(x)"):
            html += line(text + "=" + formula(sp.rem(value, S * S + C * C - 1, C)))
    raw = sp.rem(a.raw, S * S + C * C - 1, C)
    for b in factor_branches(raw, S, a.allow_inverse):
        html += polynomial(b, allow_inverse=a.allow_inverse)
    return html


def proof(a):
    from .exam_trigonometric_proof import families

    d = a.log_product.equality.identity
    intro = "<p>Преобразуем исходные логарифмы на их области определения:</p>"
    html = line(a.original)
    if d.kind == "power":
        html += power_steps(a)
    elif d.kind == "chain":
        html += chain_steps(a)
    else:
        html += domain(a)
        steps, first, second = substitution(a)
        html += steps
        if d.stage == "after-substitution":
            intro, html = html, ""
        html += back_substitution(a, first, second)
    html += "<p>Проверим кандидаты по всем исходным ограничениям:</p>"
    html += "".join(
        rejections(a, b) for b in factor_branches(a.raw, a.preferred, a.allow_inverse)
    )
    html += "<p>Исходной области определения удовлетворяют серии:</p>"
    html += "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
    return intro, html
