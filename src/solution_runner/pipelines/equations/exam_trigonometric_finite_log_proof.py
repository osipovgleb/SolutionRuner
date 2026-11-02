"""Keep amplitude, sum-to-product and finite original-domain selection in order."""

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_log_identity_proof import log


def domain(a):
    from .exam_trigonometric_log_product import conditions
    from .exam_trigonometric_proof import formula

    d = a.log_product.equality.identity
    names = {value: text for text, value in a.identities}
    names.update(
        {
            sp.expand(v): t
            for atom, texts in zip(d.atoms, d.texts, strict=True)
            for v, t in zip((atom.base, atom.argument), texts, strict=True)
        }
    )
    html = ""
    for p, relation in dict.fromkeys(conditions(a)):
        if p.free_symbols:
            html += line(
                names.get(p, formula(p)) + (">0" if relation == "positive" else r"\ne0")
            )
    for lo, hi in d.finite_base.intervals:
        html += line(sp.latex(lo) + "<x<" + sp.latex(hi))
    return html


def reduction(a):
    from .exam_exponential import X
    from .exam_trigonometric_proof import formula
    from .exam_trigonometric_radical_equation import trig_polynomial

    d = a.log_product.equality.identity
    base, argument = d.texts[0]
    fixed = sp.latex(d.atoms[1].base)
    phase = d.finite_base.phase
    denominator = trig_polynomial("sin", sp.Integer(3))
    numerator = sp.cancel(d.atoms[0].argument * denominator / d.atoms[1].base)
    html = "<p>При этих условиях применим к правой части формулу:</p>"
    html += line(r"\frac{1}{\log_a b}=\log_b a")
    html += line(log(fixed, base) + r"\ne0\iff " + base + r"\ne1")
    html += line(log(base, argument) + "=" + log(base, fixed))
    html += line(argument + "=" + fixed)
    html += line(formula(numerator) + r"=\sin 3x")
    angle = sp.latex(X + phase * sp.pi)
    html += line(r"\sin\left(" + angle + r"\right)-\sin3x=0")
    html += "<p>Преобразуем разность синусов в произведение:</p>"
    html += line(
        r"2\sin\left("
        + sp.latex(phase * sp.pi / 2 - X)
        + r"\right)\cos\left("
        + sp.latex(2 * X + phase * sp.pi / 2)
        + r"\right)=0"
    )
    html += line(
        r"\sin\left("
        + sp.latex(X - phase * sp.pi / 2)
        + r"\right)=0\quad\text{или}\quad\cos\left("
        + sp.latex(2 * X + phase * sp.pi / 2)
        + r"\right)=0"
    )
    return html


def finite_steps(a):
    from .exam_trigonometric_log_product import failed
    from .exam_trigonometric_proof import formula, pi, series_lines

    data = a.log_product.equality.identity.finite_base
    html = ""
    for text in series_lines(data.families):
        html += line(text + r",\quad k\in\mathbb Z")
    html += "<p>Объединим серии кандидатов, затем проверим исходную область определения:</p>"
    for text in series_lines(data.series()):
        html += line(text + r",\quad k\in\mathbb Z")
    seen = set()
    names = {value: text for text, value in a.identities}
    for q, p, start, end, values in data.rows():
        family = series_lines(((q, p),))[0].removeprefix("x=")
        lo, hi = data.intervals[0]
        html += line(sp.latex(lo) + "<" + family + "<" + sp.latex(hi))
        html += line(
            sp.latex(sp.simplify((lo / sp.pi - q) / p))
            + "<k<"
            + sp.latex(sp.simplify((hi / sp.pi - q) / p))
        )
        html += line(
            r"k\in\{" + ";".join(str(k) for k in range(start, end + 1)) + r"\}"
        )
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            html += line("x=" + pi(value))
            rejection = failed(a, value)
            if rejection is not None:
                expression, _, result = rejection
                html += line(
                    names.get(expression, formula(expression)) + "=" + sp.latex(result)
                )
                html += (
                    "<p>Это значение нарушает исходное ограничение и исключается.</p>"
                )
            else:
                html += "<p>Все исходные ограничения выполнены.</p>"
    return html


def proof(a):
    from .exam_trigonometric_proof import pi

    html = domain(a) + reduction(a) + finite_steps(a)
    if a.finite_roots:
        html += (
            "<p>Из найденной серии исходным ограничениям удовлетворяет только корень:</p>"
            if len(a.finite_roots) == 1
            else "<p>Исходным ограничениям удовлетворяют корни:</p>"
        )
        html += line(
            "x=" + pi(a.finite_roots[0])
            if len(a.finite_roots) == 1
            else r"x\in\{" + ";".join(pi(q) for q in a.finite_roots) + r"\}"
        )
    else:
        html += "<p>В исходной области определения корней нет.</p>"
    return "<p>Заметим, что должны быть выполнены следующие условия:</p>", html
