"""Keep log products, certified division and the parent's later candidate check."""

from functools import cmp_to_key

import sympy as sp

from ..probability.common import line
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_log_linear import branches
from .exam_trigonometric_log_product import conditions, failed
from .exam_trigonometric_log_product_proof import branches_proof


def logarithm(base, text):
    return r"\log_{" + sp.latex(base) + r"}\left(" + text + r"\right)"


def domain(a):
    from .exam_trigonometric_proof import formula

    html = "<p>Сохраним условия существования обоих исходных логарифмов:</p>"
    texts = iter(
        (a.log_product.equality.argument_text, a.log_product.equality.right_text)
    )
    for p, relation in conditions(a):
        html += line(
            (next(texts) if relation == "positive" else formula(p))
            + (">0" if relation == "positive" else r"\ne0")
        )
    args = (a.log_product.argument, a.log_product.equality.other_argument)
    for variable in (S, C):
        if all(
            p.free_symbols == {variable}
            and sp.degree(p, variable) == 1
            and p.coeff(variable).is_positive is True
            for p in args
        ):
            bound = max(
                (-p.subs(variable, 0) / p.coeff(variable) for p in args),
                key=cmp_to_key(compare),
            )
            html += line(formula(variable) + ">" + sp.latex(bound))
    return html


def conversion(a):
    data = a.log_product
    e = data.equality
    d = e.linear
    texts = (e.argument_text, e.right_text)
    html = ""
    for base, multiplier, text in zip(d.bases, d.multipliers, texts, strict=True):
        if multiplier != 1:
            b = (
                sp.latex(base)
                if base.is_Integer
                else r"\left(" + sp.latex(base) + r"\right)"
            )
            html += line(b + "^{" + sp.latex(multiplier) + "}=" + sp.latex(data.base))
            html += line(
                logarithm(base, text)
                + "="
                + sp.latex(multiplier)
                + r"\cdot"
                + logarithm(data.base, text)
            )
    if d.common != 1:
        html += "<p>Сократим общий ненулевой коэффициент при логарифмах:</p>"
    if d.sign == -1 and d.level == 0:
        return html + line(
            logarithm(data.base, texts[0]) + "=" + logarithm(data.base, texts[1])
        )
    html += line(
        logarithm(data.base, texts[0])
        + ("+" if d.sign == 1 else "-")
        + logarithm(data.base, texts[1])
        + "="
        + sp.latex(d.level)
    )
    return html


def reduction(a):
    data = a.log_product
    e = data.equality
    d = e.linear
    if d.sign == -1 and d.level == 0:
        return (
            "<p>На исходной области определения логарифмы одного основания равны тогда и только тогда, когда равны их аргументы:</p>"
            + circle_steps(a)
        )
    combined = (
        r"\left("
        + e.argument_text
        + r"\right)"
        + (
            r"\cdot\left(" + e.right_text + r"\right)"
            if d.sign == 1
            else r"/\left(" + e.right_text + r"\right)"
        )
    )
    html = (
        "<p>Перейдём к следствию, объединив логарифмы. После решения проверим оба исходных аргумента:</p>"
        if d.implication
        else "<p>На исходной области определения объединим логарифмы:</p>"
    )
    html += line(
        (r"\Rightarrow\quad" if d.implication else r"\Longleftrightarrow\quad")
        + logarithm(data.base, combined)
        + "="
        + sp.latex(d.level)
    )
    target = sp.simplify(data.base**d.level)
    html += line(combined + "=" + sp.latex(target))
    if d.product_identity and d.projection is not None:
        return (
            html
            + line(combined + "=" + d.product_identity[0])
            + line(d.product_identity[0] + "=" + sp.latex(target))
        )
    return html + circle_steps(a)


def circle_steps(a):
    from .exam_trigonometric_proof import formula

    data = a.log_product
    e = data.equality
    d = e.linear
    target = sp.simplify(data.base**d.level)
    html = ""
    for text, value in a.identities:
        if text not in (r"\sin(x)", r"\cos(x)"):
            if data.divide == S:
                value = sp.rem(value, S * S + C * C - 1, C)
            html += line(text + "=" + formula(value))
    if d.sign == -1:
        first = data.argument
        if data.divide == S:
            first = sp.rem(first, S * S + C * C - 1, C)
        html += line(
            formula(first)
            + "="
            + formula(e.other_argument if target == 1 else target * e.other_argument)
        )
    html += line(formula(data.factor) + "=0")
    if data.divide != 1:
        coefficient = sp.cancel(e.other_argument / data.divide)
        name = formula(data.divide)
        html += line(
            name
            + (">0" if coefficient.is_positive else "<0")
            + r"\quad\Longrightarrow\quad"
            + name
            + r"\ne0"
        )
        html += "<p>Этот множитель не равен нулю на исходной области определения, поэтому разделим на него:</p>"
        html += line(formula(sp.cancel(data.factor / data.divide)) + "=0")
    return html


def doubled_candidates(a, source):
    from .exam_trigonometric_inverse import level_series
    from .exam_trigonometric_proof import formula, series_lines

    identity = a.log_product.equality.linear.product_identity
    html = (
        "<p>Применим формулу приведения и решим полученное уравнение:</p>"
        if identity
        else "<p>Используем синус двойного угла и решим полученное уравнение:</p>"
    )
    html += (
        "".join(line(s) for s in identity[1:])
        if identity
        else line(r"\sin 2x=2\sin x\cos x")
    )
    for b in source:
        html += line(formula(b.polynomial, "2x") + "=0")
        for v in b.values:
            html += line(r"\sin 2x=" + sp.latex(v))
            original = level_series(S, v, a.allow_inverse)
            html += "".join(
                line(f.replace("x=", "2x=", 1) + r",\quad k\in\mathbb Z")
                for f in series_lines(original)
            )
            html += "".join(
                line(f + r",\quad k\in\mathbb Z")
                for f in series_lines(tuple((q / 2, p / 2) for q, p in original))
            )
    return html


def checks(a, source):
    from .exam_trigonometric_proof import formula, pi

    html = "<p>Аргументы исходных логарифмов имеют период 2π. Проверим представителей каждой серии по модулю 2π:</p>"
    data = a.log_product
    e = data.equality
    names = {data.argument: e.argument_text, e.other_argument: e.right_text}
    for b in source:
        for q in b.residues:
            rejection = failed(a, q)
            if rejection is not None:
                p, rel, v = rejection
                html += line(
                    "x="
                    + pi(q)
                    + r"+2\pi k:\quad"
                    + names.get(p, formula(p))
                    + "="
                    + sp.latex(v)
                    + (r"\not>0" if rel == "positive" else "=0")
                )
                html += "<p>Исходное выражение не определено; эту серию исключаем.</p>"
                continue
            substitution = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
            values = [
                (p, sp.simplify(p.subs(substitution)))
                for p, rel in conditions(a)
                if rel == "positive"
            ]
            html += line(
                "x="
                + pi(q)
                + r"+2\pi k:\quad"
                + r",\quad".join(
                    names.get(p, formula(p)) + "=" + sp.latex(v) + ">0"
                    for p, v in values
                )
            )
    return html


def proof(a):
    from .exam_trigonometric_proof import families

    d = a.log_product.equality.linear
    source = branches(a, a.preferred, a.allow_inverse)
    html = line(a.original)
    if d.domain_first:
        html += domain(a)
    html += conversion(a)
    if not d.implication and not d.domain_first:
        html += domain(a)
    html += reduction(a)
    if d.projection is not None:
        html += doubled_candidates(a, source)
    elif d.implication:
        from .exam_trigonometric_proof import polynomial

        html += "".join(
            polynomial(b, factorization=False, allow_inverse=a.allow_inverse)
            for b in source
        )
    else:
        html += branches_proof(a, source, False, factorization=False)
    prefix = ""
    if d.image_after_candidates:
        prefix, html = html, ""
    if d.implication:
        html += domain(a) + checks(a, source)
    html += "<p>С учётом исходной области определения получаем серии корней:</p>"
    html += "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
    return prefix or "<p>Преобразуем исходные логарифмы:</p>", html
