"""Show reciprocal base change, a positive product split and the parent's linear t."""

import sympy as sp

from ..probability.common import line


def steps(a):
    from .exam_trigonometric_log_identity import Z
    from .exam_trigonometric_log_identity_proof import domain, log
    from .exam_trigonometric_proof import formula

    d = a.log_product.equality.identity
    data = d.base_change
    name = d.substitution
    t = sp.Symbol(name, real=True)
    base = sp.latex(data.offset - t)
    other = sp.latex(data.offset + t)
    fixed = sp.latex(d.atoms[1].base)
    html = "<p>Пусть:</p>" + line(formula(d.converted) + "=" + name)
    html += domain(a)
    html += line("0\\le " + name + "<" + sp.latex(data.offset))
    html += line(name + r"\ne " + sp.latex(data.offset - 1))
    html += "<p>Ненулевой исходный логарифм в знаменателе позволяет перейти к обратному основанию:</p>"
    html += line(log(fixed, base) + r"\ne0\iff " + base + r"\ne1")
    html += line(r"\frac{1}{" + log(fixed, base) + "}=" + log(base, fixed))
    html += line(log(base, sp.latex(data.offset**2 - t**2)) + "=2+" + log(base, fixed))
    html += "<p>Разложим аргумент на положительные множители и воспользуемся свойством логарифма произведения:</p>"
    html += line(
        sp.latex(data.offset**2 - t**2)
        + r"=\left("
        + base
        + r"\right)\left("
        + other
        + r"\right)"
    )
    html += line("1+" + log(base, other) + "=2+" + log(base, fixed))
    html += line(log(base, sp.latex((data.offset + t) / d.atoms[1].base)) + "=1")
    html += line(sp.latex((data.offset + t) / d.atoms[1].base) + "=" + base)
    html += line(sp.latex(d.polynomial.subs(Z, t)) + "=0")
    html += line(name + "=" + sp.latex(data.target))
    html += "<p>Вернёмся к исходной переменной:</p>"
    html += line(formula(d.converted) + "=" + sp.latex(data.target))
    level = sp.cancel(data.target / data.weight)
    html += line(formula(data.variable**2) + "=" + sp.latex(level))
    if 0 <= level <= 1:
        html += line(formula(data.variable) + r"=\pm " + sp.latex(sp.sqrt(level)))
    else:
        html += "<p>Квадрат тригонометрической функции должен лежать в отрезке от 0 до 1.</p>"
    return html
