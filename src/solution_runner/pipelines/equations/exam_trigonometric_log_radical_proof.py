"""Retain the original domain-first proof and the later case-by-case alternative."""

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import S
from .exam_trigonometric_log_product import conditions, ratio_factor, zero_cases
from .exam_trigonometric_log_product_proof import branches_proof, logarithm
from .exam_trigonometric_radical_product import factor_branches


def domain(a):
    from .exam_trigonometric_inverse import angles
    from .exam_trigonometric_proof import formula, pi

    data = a.log_product
    root = data.radical
    html = "<p>Найдём область допустимых значений исходного уравнения:</p>"
    relations = {"nonzero": r"\ne0", "positive": ">0", "nonnegative": r"\ge0"}
    order = [data.factor, data.argument, root.denominator, *a.poles]
    for expression, relation in sorted(
        conditions(a), key=lambda item: order.index(item[0])
    ):
        html += line(formula(ratio_factor(expression)) + relations[relation])
    lower = sp.simplify(-data.factor.subs(S, 0) / data.factor.coeff(S))
    html += line(r"\sin x\ge" + sp.latex(lower))
    if root.divide:
        html += line(
            r"\cos x<0,\quad\tg x<0\quad\Longleftrightarrow\quad\sin x>0,\quad\cos x<0"
        )
        html += "<p>При полученных ограничениях оба подкоренных выражения строго положительны:</p>"
        html += line(
            formula(data.factor) + ">" + sp.latex(data.factor.subs(S, 0)) + ">0"
        )
        html += line(formula(ratio_factor(root.denominator)) + ">0")
        html += "<p>Поэтому оба корня ненулевые, и на них можно сократить. Следовательно:</p>"
    else:
        html += line(r"\cos x>0")
        start = next(
            q - 2 if q > 1 else q
            for q in angles(S, lower, False)
            if sp.cos(q * sp.pi) > 0
        )
        html += line(
            pi(start)
            + r"+2\pi k\le x<\frac{\pi}{2}+2\pi k,\quad k\in\mathbb Z.\quad(*)"
        )
    return html


def case_steps(a, *, separate=False):
    from .exam_trigonometric_proof import formula

    data = a.log_product
    html = ""
    for log_case, value in zero_cases(data):
        if log_case:
            html += "<p>Логарифм равен нулю тогда и только тогда, когда его аргумент равен единице:</p>"
            html += line(logarithm(data.base, data.argument) + "=0")
            if separate:
                html += line(
                    r"\begin{cases}"
                    + formula(data.argument)
                    + "=1"
                    + r"\\"
                    + formula(data.factor)
                    + r"\ge0\end{cases}"
                )
            else:
                html += line(formula(data.argument) + "=1")
        else:
            html += "<p>Первый случай: корень равен нулю, а аргумент логарифма остаётся положительным:</p>"
            html += line(r"\sqrt{" + formula(data.factor) + "}=0")
            html += line(
                r"\begin{cases}"
                + formula(data.factor)
                + "=0"
                + r"\\"
                + formula(data.argument)
                + r">0\end{cases}"
            )
        html += branches_proof(
            a, factor_branches(value, a.preferred, a.allow_inverse), log_case
        )
    return html


def conclusion(a):
    from .exam_trigonometric_proof import families

    return "<p>С учётом исходных ограничений получаем:</p>" + "".join(
        line(f + r",\quad k\in\mathbb Z") for f in families(a)
    )


def proof(a):
    intro = domain(a)
    steps = (
        ""
        if a.log_product.radical.divide
        else "<p>При этих условиях произведение равно нулю тогда и только тогда, когда хотя бы один множитель равен нулю. Сохраним оба случая:</p>"
    )
    return intro, steps + case_steps(a) + conclusion(a)


def alternative(a, image):
    from .exam_trigonometric_proof import formula

    data = a.log_product
    if not data.radical.alternative:
        return ""
    html = "<p><b>Изложим решение пункта а) иначе.</b></p>" + image
    html += "<p>Преобразуем уравнение, задавая ограничения отдельно для каждого нулевого множителя:</p>"
    html += line(a.original)
    html += line(
        r"\left[\begin{aligned}&\begin{cases}"
        + formula(data.factor)
        + r"=0\\"
        + formula(data.argument)
        + r">0\end{cases}\\&\begin{cases}"
        + formula(data.argument)
        + r"=1\\"
        + formula(data.factor)
        + r"\ge0\end{cases}\end{aligned}\right."
    )
    return html + case_steps(a, separate=True) + conclusion(a)
