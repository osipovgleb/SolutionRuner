"""One contact-system solution, with the tangent f and the curve g."""

from html import escape

import sympy as sp

from ..probability.common import line
from .common import X


def tex(expression, **settings):
    """Keep polynomial powers descending even when a coefficient is symbolic."""
    expression = sp.sympify(expression)
    parts = []
    for (power,), coefficient in sp.Poly(expression, X).terms():
        term = coefficient * X**power
        negative = term.could_extract_minus_sign()
        body = sp.latex(-term if negative else term, **settings)
        if not parts:
            parts.append(("-" if negative else "") + body)
        else:
            parts.append((" - " if negative else " + ") + body)
    return "".join(parts)


def inline(formula):
    return '<span data-inline-latex="' + escape(formula, quote=True) + '"></span>'


def system(first, second):
    return line(r"\begin{cases}" + first + r"\\" + second + r"\end{cases}")


def substitute(expression, value):
    value = sp.sympify(value)
    number = tex(value)
    if value < 0 or value.is_Integer is not True:
        number = r"\left(" + number + r"\right)"
    return tex(expression, symbol_names={X: number}, mul_symbol="dot")


def intro(contact):
    tangent = contact.line
    if contact.parallel:
        tangent = sp.diff(contact.line, X) * X - sp.Symbol("b", real=True)
        reason = (
            " — касательная, параллельная данной прямой "
            + inline("y=" + tex(contact.line))
            + " (их угловые коэффициенты равны, а свободный член касательной пока неизвестен), а "
        )
    else:
        reason = " — данная касательная, а "
    html = (
        "<p>Пусть "
        + inline("f(x)=" + tex(tangent))
        + reason
        + inline("g(x)=" + tex(contact.curve))
        + " — заданная функция.</p>"
        + "<p>Составим систему условий касания:</p>"
    )
    html += system(
        r"f(x)=g(x),&\text{так как графики пересекаются}",
        r"f'(x)=g'(x),&\text{так как }f(x)\text{ — касательная к }g(x)",
    )
    html += system(
        tex(tangent) + "=" + tex(contact.curve),
        tex(sp.diff(tangent, X)) + "=" + tex(sp.diff(contact.curve, X)),
    )
    return html


def coordinate(contact):
    derivative = sp.diff(contact.curve, X)
    slope = sp.diff(contact.line, X)
    equation = sp.expand(derivative - slope)
    html = "<p>Из второго уравнения найдём абсциссу точки касания:</p>"
    roots = contact.candidates
    if sp.Poly(equation, X).degree() == 2:
        from bs4 import BeautifulSoup

        from ..function_graphs.parabola_proof import quadratic_steps

        html += "<p>Решим квадратное уравнение через дискриминант:</p>"
        steps = BeautifulSoup(quadratic_steps(equation, X, roots), "html.parser")
        from ..word_problems.math_common import primitive

        polynomial = sp.Poly(primitive(equation, (X,)), X)
        a, b, c = polynomial.all_coeffs()
        discriminant = b**2 - 4 * a * c
        for node in steps.select("[data-inline-latex]"):
            formula = node["data-inline-latex"].split(r"\in\left\{", 1)[0]
            if r"\pm" in formula:
                rows = []
                for sign, symbol in ((-1, "-"), (1, "+")):
                    root = sp.simplify((-b + sign * sp.sqrt(discriminant)) / (2 * a))
                    row = formula.replace("x=", "x&=", 1).replace(r"\pm", symbol)
                    rows.append(row + "=" + tex(root))
                    if discriminant == 0:
                        break
                formula = (
                    r"\left[\begin{aligned}"
                    + r"\\".join(rows)
                    + r"\end{aligned}\right."
                    if len(rows) > 1
                    else rows[0].replace("x&=", "x=", 1)
                )
            node["data-inline-latex"] = (
                r"\displaystyle " + formula if r"\frac" in formula else formula
            )
        html += str(steps)
    else:
        html += line(tex(equation) + "=0")
        html += line("x=" + tex(roots[0]))
    if contact.parallel:
        x0 = contact.valid[0]
        b = sp.expand(slope * X - contact.curve)
        value = sp.simplify(b.subs(X, x0))
        html += "<p>Подставим найденную абсциссу в первое уравнение системы:</p>"
        html += line("b=" + substitute(b, x0) + "=" + tex(value))
        html += system("x=" + tex(x0), "b=" + tex(value))
    else:
        html += "<p>Проверим найденные значения в первом уравнении системы:</p>"
        for root in roots:
            fv = sp.simplify(contact.line.subs(X, root))
            gv = sp.simplify(contact.curve.subs(X, root))
            html += line(
                "f("
                + tex(root)
                + ")="
                + tex(fv)
                + ("=" if fv == gv else r"\ne")
                + tex(gv)
                + "=g("
                + tex(root)
                + ")"
            )
        x0 = contact.valid[0]
        html += line("x=" + tex(x0))
    if contact.quantity == "y":
        html += "<p>Найдём ординату точки касания:</p>"
        html += line(
            "y=g("
            + tex(x0)
            + ")="
            + substitute(contact.curve, x0)
            + "="
            + tex(contact.result)
        )
    return html


def parameter(contact):
    a, b, c = (sp.expand(contact.curve).coeff(X, p) for p in (2, 1, 0))
    k, l = sp.diff(contact.line, X), contact.line.subs(X, 0)
    p = contact.parameter
    x0, value = contact.valid[0]
    if a == p:
        product = sp.simplify((k - b) / 2)
        html = "<p>Из второго уравнения выразим произведение параметра и абсциссы:</p>"
        html += line(tex(p * X) + "=" + tex(product))
        # ax² = (ax)x; the first equation stays a point-of-intersection equation.
        replaced = sp.expand(product * X + b * X + c)
        html += "<p>Подставим это выражение в первое уравнение системы:</p>"
        html += line(tex(contact.line) + "=" + tex(replaced))
        html += line(tex(sp.expand(contact.line - replaced)) + "=0")
        html += line("x=" + tex(x0))
        html += line(
            tex(p) + "=" + tex(product) + " : " + substitute(X, x0) + "=" + tex(value)
        )
    elif b == p:
        expressed = sp.expand(k - 2 * a * X)
        html = "<p>Из второго уравнения выразим параметр и подставим в первое:</p>"
        html += line(tex(p) + "=" + tex(expressed))
        # Keep the actual substitution visible before simplifying.
        polynomial = tex(a * X**2) + "+\\left(" + tex(expressed) + r"\right)x"
        polynomial += ("+" if c >= 0 else "") + tex(c)
        html += line(tex(contact.line) + "=" + polynomial)
        html += line(
            tex(sp.expand(contact.line - (a * X**2 + expressed * X + c))) + "=0"
        )
        html += line("x^2=" + tex(sp.simplify((c - l) / a)))
        html += line(
            r"\quad\text{или}\quad ".join("x=" + tex(x) for x, _ in contact.candidates)
        )
        if contact.sign:
            html += (
                "<p>По условию абсцисса точки касания "
                + ("положительна" if contact.sign > 0 else "отрицательна")
                + ", поэтому "
                + inline("x=" + tex(x0))
                + ".</p>"
            )
        html += line(tex(p) + "=" + substitute(expressed, x0) + "=" + tex(value))
    else:
        derivative = sp.diff(contact.curve, X)
        html = "<p>Из второго уравнения найдём абсциссу точки касания:</p>"
        html += line(tex(sp.expand(derivative - k)) + "=0")
        html += line("x=" + tex(x0))
        html += "<p>Подставим найденное значение в первое уравнение системы и выразим параметр:</p>"
        html += line(substitute(contact.line, x0) + "=" + substitute(contact.curve, x0))
        expression = sp.expand(contact.line - (contact.curve - p))
        html += line(tex(p) + "=" + substitute(expression, x0) + "=" + tex(value))
    return html


def render(contact):
    return intro(contact) + (
        coordinate(contact) if contact.parameter is None else parameter(contact)
    )
