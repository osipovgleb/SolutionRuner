"""Derivative/contact systems and the source's alternative discriminant method."""

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .common import X, real_roots


def _system(contact):
    derivative = sp.diff(contact.curve, X)
    slope = sp.diff(contact.line, X)
    return (
        r"\begin{cases}"
        + sp.latex(derivative)
        + "="
        + sp.latex(slope)
        + r"\\"
        + sp.latex(contact.curve)
        + "="
        + sp.latex(contact.line)
        + r"\end{cases}"
    )


def _known(contact):
    derivative = sp.diff(contact.curve, X)
    slope = sp.diff(contact.line, X)
    html = "<p>Угловой коэффициент касательной равен производной в точке касания. Найдём его по данной прямой:</p>"
    html += line("y=" + sp.latex(contact.line) + r",\quad k=" + sp.latex(slope))
    html += line("f'(x)=" + sp.latex(derivative))
    html += "<p>Приравняем производную угловому коэффициенту:</p>"
    html += line(sp.latex(derivative) + "=" + sp.latex(slope))
    html += line(r"x\in\{" + ",".join(sp.latex(r) for r in contact.candidates) + r"\}")
    if not contact.parallel:
        html += "<p>Касательная проходит через точку графика. Проверим найденные абсциссы в исходном уравнении пересечения:</p>"
        for root in contact.candidates:
            residue = sp.simplify((contact.curve - contact.line).subs(X, root))
            html += line(
                "f("
                + sp.latex(root)
                + ")-("
                + sp.latex(contact.line.subs(X, root))
                + ")="
                + sp.latex(residue)
                + ("" if residue == 0 else r"\ne0")
            )
    x0 = contact.valid[0]
    html += line("x_0=" + sp.latex(x0))
    if contact.quantity == "y":
        html += "<p>Найдём ординату по уравнению касательной:</p>"
        substituted = sp.latex(contact.line, symbol_names={X: "(" + sp.latex(x0) + ")"})
        html += line("y_0=" + substituted + "=" + sp.latex(contact.result))
    return html


def _parameter(contact):
    a, b, c = (sp.expand(contact.curve).coeff(X, p) for p in [2, 1, 0])
    k, l = sp.diff(contact.line, X), contact.line.subs(X, 0)
    parameter = contact.parameter
    x0, value = contact.valid[0]
    html = "<p>Запишем оба условия касания: совпадение угловых коэффициентов и общей точки:</p>"
    html += line(r"\begin{cases}f'(x_0)=k\\f(x_0)=kx_0+l\end{cases}")
    html += line(_system(contact))
    html += "<p>Выразим параметр из условия на производную и подставим в уравнение общей точки:</p>"
    if a == parameter:
        delta = k - b
        html += line(rf"{parameter}x_0=\frac{{{sp.latex(delta)}}}{{2}}")
        html += line(rf"-\frac{{{sp.latex(delta)}}}{{2}}x_0+({sp.latex(c - l)})=0")
        html += line("x_0=" + sp.latex(x0))
        html += line(
            rf"{parameter}=\frac{{{sp.latex(delta)}}}{{2({sp.latex(x0)})}}={sp.latex(value)}"
        )
    elif b == parameter:
        html += line(rf"{parameter}=({sp.latex(k)})-2({sp.latex(a)})x_0")
        html += line(rf"x_0^2=\frac{{{sp.latex(c - l)}}}{{{sp.latex(a)}}}")
        html += line(
            r"x_0\in\{" + ",".join(sp.latex(x) for x, _ in contact.candidates) + r"\}"
        )
        if contact.sign:
            html += "<p>Выберем корень с заданным знаком абсциссы:</p>"
            html += line(
                "x_0"
                + (">0" if contact.sign > 0 else "<0")
                + r",\quad x_0="
                + sp.latex(x0)
            )
        html += line(
            rf"{parameter}=({sp.latex(k)})-2({sp.latex(a)})({sp.latex(x0)})={sp.latex(value)}"
        )
    else:
        html += line(rf"2({sp.latex(a)})x_0+({sp.latex(b)})={sp.latex(k)}")
        html += line("x_0=" + sp.latex(x0))
        html += line(
            rf"{parameter}=({sp.latex(l)})+({sp.latex(a)})({sp.latex(x0)})^2={sp.latex(value)}"
        )
    return html


def _discriminant(contact):
    a, b, c = (sp.expand(contact.curve).coeff(X, p) for p in [2, 1, 0])
    k, l = sp.diff(contact.line, X), contact.line.subs(X, 0)
    discriminant = sp.expand((b - k) ** 2 - 4 * a * (c - l))
    roots = real_roots(discriminant, contact.parameter)
    valid = []
    checks = []
    for root in roots:
        av, bv = a.subs(contact.parameter, root), b.subs(contact.parameter, root)
        if av == 0:
            continue
        point = sp.simplify((k - bv) / (2 * av))
        checks.append((root, point))
        curve = contact.curve.subs(contact.parameter, root)
        if contact.sign is not None and sp.sign(point) != contact.sign:
            continue
        if sp.simplify((curve - contact.line).subs(X, point)) == 0:
            valid.append(root)
    if set(valid) != {contact.result}:
        raise UnsupportedCondition("the independent discriminant method disagrees")
    html = "<p>Второй способ. Касательная имеет с параболой одну общую точку. При ненулевом старшем коэффициенте уравнение пересечения имеет двойной корень:</p>"
    html += line(sp.latex(sp.expand(contact.curve - contact.line)) + "=0")
    html += line("D=" + sp.latex(discriminant) + "=0")
    html += line(
        str(contact.parameter) + r"\in\{" + ",".join(sp.latex(r) for r in roots) + r"\}"
    )
    if contact.sign:
        html += "<p>Проверим знак абсциссы двойного корня для каждого параметра:</p>"
        for root, point in checks:
            html += line(
                str(contact.parameter)
                + "="
                + sp.latex(root)
                + r"\ \Longrightarrow\ x_0="
                + sp.latex(point)
            )
    html += line(str(contact.parameter) + "=" + sp.latex(contact.result))
    return html


def render(contact, *, two_methods=False):
    if two_methods and contact.parallel:
        raise UnsupportedCondition(
            "the parallel-line source has no second contact method"
        )
    html = "<p>Первый способ.</p>" if two_methods else ""
    html += _known(contact) if contact.parameter is None else _parameter(contact)
    if two_methods:
        if contact.parameter is not None:
            html += _discriminant(contact)
        else:
            html += "<p>Второй способ. Запишем условие касания в виде системы:</p>"
            html += line(_system(contact))
            html += line(
                r"\begin{cases}"
                + sp.latex(
                    sp.expand(sp.diff(contact.curve, X) - sp.diff(contact.line, X))
                )
                + r"=0\\"
                + sp.latex(sp.expand(contact.curve - contact.line))
                + r"=0\end{cases}"
            )
            html += "<p>Подстановка найденных кандидатов в оба уравнения оставляет общую точку:</p>"
            html += line("x_0=" + sp.latex(contact.valid[0]))
    return html
