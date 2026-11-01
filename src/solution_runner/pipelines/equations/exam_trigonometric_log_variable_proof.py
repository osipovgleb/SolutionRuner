"""Show original base restrictions before the parent's polynomial reduction."""

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S, U
from .exam_trigonometric_log_product_proof import rejections
from .exam_trigonometric_log_variable_methods import (
    cosine_double,
    cotangent,
    cotangent_double,
    quadratic,
)
from .exam_trigonometric_radical_product import factor_branches


def domain(a):
    from .exam_trigonometric_proof import formula

    d = a.log_product.equality.variable
    html = "<p>Сохраним область определения исходного логарифма:</p>"
    html += (
        line(d.base_text + ">0")
        + line(d.base_text + r"\ne1")
        + line(d.argument_text + ">0")
    )
    variable = S if d.base.has(S) else C
    coefficient = d.base.coeff(variable)
    if abs(coefficient) != 1:
        html += line(formula(variable) + (">0" if coefficient.is_positive else "<0"))
    if abs(coefficient) == 1:
        html += line(
            ("0<" + formula(variable) + "<1")
            if coefficient == 1
            else ("-1<" + formula(variable) + "<0")
        )
    return html


def definition(a):
    from .exam_trigonometric_proof import formula

    d = a.log_product.equality.variable
    html = "<p>На этой области применим определение логарифма:</p>"
    if d.multiplier != 1:
        html += line(
            r"\log_{"
            + d.base_text
            + r"}\left("
            + d.argument_text
            + r"\right)=\log_{"
            + d.base_text
            + r"}\left("
            + sp.latex(d.multiplier)
            + r"\left("
            + d.base_text
            + r"\right)^{"
            + sp.latex(d.level)
            + r"}\right)"
        )
    html += line(
        d.argument_text
        + "="
        + (sp.latex(d.multiplier) + r"\cdot" if d.multiplier != 1 else "")
        + r"\left("
        + d.base_text
        + r"\right)^{"
        + sp.latex(d.level)
        + "}"
        + ("=1" if d.level == 0 else "")
    )
    html += "<p>Раскроем аргументы с помощью тригонометрических тождеств:</p>"
    if d.method in ("cos_double", "cot_double"):
        return html
    for text, value in a.identities:
        if text not in (r"\sin(x)", r"\cos(x)"):
            if d.method == "quadratic":
                variable, _ = quadratic(a.raw)
                value = sp.rem(value, S * S + C * C - 1, C if variable == S else S)
            html += line(text + "=" + formula(value))
    return html


def quadratic_steps(a):
    from .exam_trigonometric_proof import formula, polynomial

    variable, p = quadratic(a.raw)
    other = C if variable == S else S
    html = ""
    if not any(text not in (r"\sin(x)", r"\cos(x)") for text, _ in a.identities):
        html += line(formula(other**2) + "=" + formula(1 - variable**2))
    for b in factor_branches(p, variable, a.allow_inverse):
        html += polynomial(
            b, allow_inverse=a.allow_inverse, sine_inverse=a.sine_inverse
        )
    return html


def angle_series(variable, value, scale, allow_inverse, candidate=()):
    from .exam_trigonometric_inverse import level_series
    from .exam_trigonometric_proof import series_lines

    series = (
        tuple((q * scale, p * scale) for q, p in candidate)
        if candidate
        else level_series(variable, value, allow_inverse)
    )
    html = (
        "".join(
            line(f.replace("x=", "2x=", 1) + r",\quad k\in\mathbb Z")
            for f in series_lines(series)
        )
        if scale == 2
        else ""
    )
    return html + "".join(
        line(f + r",\quad k\in\mathbb Z")
        for f in series_lines(tuple((q / scale, p / scale) for q, p in series))
    )


def cosine_steps(a):
    from .exam_trigonometric_proof import formula

    p = cosine_double(a.raw)
    html = line(r"\sin^4x-\cos^4x=(\sin^2x-\cos^2x)(\sin^2x+\cos^2x)=-\cos2x")
    html += line(r"\cos4x=2\cos^22x-1") + line(formula(p, "2x") + "=0")
    for b in factor_branches(p, C, a.allow_inverse):
        for v in b.values:
            html += line(r"\cos2x=" + sp.latex(v)) + angle_series(
                C, v, sp.Integer(2), a.allow_inverse
            )
    return html


def cotangent_steps(a):
    from .exam_trigonometric_proof import formula

    d = a.log_product.equality.variable
    if d.method == "cot":
        factor, value = cotangent(a.raw, d.base)
        html = line(formula(a.raw) + "=0")
        html += (
            line(r"\sin x\ne0")
            + "<p>По исходной области определения синус не равен нулю. Разделим на него:</p>"
        )
        html += line(formula(factor) + "=0") + line(formula(factor / S) + "=0")
        scale = sp.S.One
    else:
        first, second, value = cotangent_double(a.raw)
        html = line(r"\sin^2x=\frac{1-\cos2x}{2}") + line(r"\cos^2x=\frac{1+\cos2x}{2}")
        html += line(formula(first * C + second * S, "2x") + "=0")
        html += "<p>При нулевом синусе двойного угла косинус равен 1 или −1, и это уравнение не выполнено. Поэтому можно разделить на синус двойного угла:</p>"
        html += line(r"\sin2x\ne0")
        scale = sp.Integer(2)
    html += line((r"\ctg2x" if scale == 2 else r"\ctg x") + "=" + sp.latex(value))
    return html + angle_series(U, value, scale, a.allow_inverse, d.candidate_series)


def proof(a):
    from .exam_trigonometric_proof import families

    d = a.log_product.equality.variable
    html = line(a.original) + domain(a) + definition(a)
    intro = "<p>Решим уравнение по определению логарифма:</p>"
    if d.image_after_definition:
        intro, html = html, ""
    if d.method == "quadratic":
        html += quadratic_steps(a)
    elif d.method == "cos_double":
        html += cosine_steps(a)
    else:
        html += cotangent_steps(a)
    html += "<p>Проверим найденные кандидаты по ограничениям исходного основания и аргумента:</p>"
    candidate_factor = cotangent(a.raw, d.base)[0] if d.method == "cot" else a.raw
    source = factor_branches(candidate_factor, a.preferred, a.allow_inverse)
    html += "".join(rejections(a, b) for b in source)
    html += "<p>Исходным ограничениям удовлетворяют серии:</p>"
    html += "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
    return intro, html
