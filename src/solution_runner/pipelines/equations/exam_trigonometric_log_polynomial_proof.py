"""Keep log substitution, direct log levels and the parent's later trig substitution."""

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_log_common import exact_power
from .exam_trigonometric_log_common_proof import expression as tex_expression
from .exam_trigonometric_log_common_proof import power_level
from .exam_trigonometric_log_common_proof import steps as common_steps
from .exam_trigonometric_log_polynomial import L
from .exam_trigonometric_log_product import conditions
from .exam_trigonometric_log_product_proof import rejections


def quadratic_steps(polynomial, variable):
    a, b, c = sp.Poly(polynomial, variable).all_coeffs()
    d = sp.simplify(b * b - 4 * a * c)
    name = sp.latex(variable)
    html = line(
        "D=("
        + sp.latex(b)
        + r")^2-4\cdot("
        + sp.latex(a)
        + r")\cdot("
        + sp.latex(c)
        + ")="
        + sp.latex(d)
    )
    html += line(
        name
        + r"=\frac{"
        + sp.latex(-b)
        + r"\pm\sqrt{"
        + sp.latex(d)
        + r"}}{"
        + sp.latex(2 * a)
        + "}"
    )
    if sp.sqrt(d) != sp.Pow(d, sp.Rational(1, 2), evaluate=False):
        html += line(r"\sqrt{" + sp.latex(d) + "}=" + sp.latex(sp.sqrt(d)))
    return html


def log_equation(a, log):
    data = a.log_polynomial
    names = {L: log}
    html = ""
    if data.factor_before:
        html += (
            "<p>Вынесем общий логарифмический множитель, сохраняя его нулевые значения:</p>"
            if data.normalization is not None
            else "<p>На исходной области определения числитель равен нулю. Вынесем общий логарифмический множитель:</p>"
        )
        html += line(
            tex_expression(data, data.polynomial, names=names, factor=True) + "=0"
        )
    if data.factor_before and not data.substitution and data.normalization is not None:
        return html
    if data.substitution:
        variable = sp.Symbol(data.substitution, real=True)
        html += "<p>Сделаем замену и решим квадратное уравнение:</p>"
        html += line(data.substitution + "=" + log)
        polynomial = data.polynomial.subs(L, variable)
        html += line(sp.latex(polynomial) + "=0")
        if data.discriminant:
            html += quadratic_steps(polynomial, variable)
        else:
            html += line(sp.latex(sp.factor(polynomial)) + "=0")
        for level in data.levels:
            html += line(data.substitution + "=" + sp.latex(level))
    else:
        html += (
            "<p>Решим квадратное уравнение относительно логарифмического выражения:</p>"
        )
        html += line(
            tex_expression(data, data.polynomial, names=names, factor=True) + "=0"
        )
    return html


def trig_case(a, level):
    from .exam_trigonometric_compile import C, S
    from .exam_trigonometric_log_method_proof import branch_notation
    from .exam_trigonometric_proof import candidate_lines, formula, polynomial
    from .exam_trigonometric_radical_product import factor_branches

    data = a.log_polynomial
    value = exact_power(data.base, level)
    log = r"\log_{" + sp.latex(data.base) + r"}\left(" + data.argument_text + r"\right)"
    html = "<p>Вернёмся к исходной переменной по определению логарифма:</p>"
    html += line(log + "=" + tex_expression(data, level))
    if level.is_Rational is not True:
        html += line(tex_expression(data, level) + "=" + power_level(data, level))
    base = (
        sp.latex(data.base)
        if data.base.is_Integer
        else r"\left(" + sp.latex(data.base) + r"\right)"
    )
    html += line(
        data.argument_text
        + "="
        + base
        + "^{"
        + power_level(data, level)
        + "}="
        + sp.latex(value)
    )
    for text, expression in a.identities:
        if text.startswith(r"\cos(2x)"):
            html += line(
                text
                + "="
                + formula(sp.expand(sp.rem(expression, S * S + C * C - 1, S)))
            )
    for b in factor_branches(sp.expand(data.argument - value), C, a.allow_inverse):
        if data.trig_substitution and sp.degree(b.polynomial, b.variable) == 2:
            variable = sp.Symbol(data.trig_substitution, real=True)
            html += line(formula(b.polynomial) + "=0")
            html += "<p>Введём тригонометрическую функцию как новую переменную:</p>"
            html += line(data.trig_substitution + "=" + formula(b.variable))
            q = b.polynomial.subs(b.variable, variable)
            html += line(sp.latex(q) + "=0")
            html += quadratic_steps(q, variable)
            steps = candidate_lines(
                b, substitution=data.trig_substitution, allow_inverse=a.allow_inverse
            )
        else:
            steps = polynomial(b, allow_inverse=a.allow_inverse)
        steps += rejections(a, b)
        html += branch_notation(a, b, False, steps)
    return html


def proof(a):
    from .exam_trigonometric_proof import families, formula

    data = a.log_polynomial
    prefix = ""
    log = r"\log_{" + sp.latex(data.base) + r"}\left(" + data.argument_text + r"\right)"
    html = line(a.original)
    html += "<p>Сохраним область определения исходного логарифма и все исходные знаменатели:</p>"
    for expression, relation in conditions(a):
        if relation == "positive" and sp.degree(data.polynomial, L) == 1:
            continue
        html += line(
            (
                data.argument_text
                if relation == "positive" and expression == data.argument
                else formula(expression)
            )
            + (">0" if relation == "positive" else r"\ne0")
        )
    html += common_steps(a, log)
    if data.powers is not None:
        e = data.powers
        names = {L: r"\left(" + log + r"\right)"}
        base = (
            sp.latex(e.base)
            if e.base.is_Integer
            else r"\left(" + sp.latex(e.base) + r"\right)"
        )
        for exponent in e.denominator_exponents:
            html += line(base + "^{" + sp.latex(exponent, symbol_names=names) + "}>0")
        html += "<p>Перейдём к одному основанию. Положительные степени с одинаковым основанием, отличным от единицы, равны тогда и только тогда, когда равны их показатели:</p>"
        left, right = (sp.latex(v, symbol_names=names) for v in (e.left, e.right))
        html += line(base + "^{" + left + "}=" + base + "^{" + right + "}")
        html += line(left + "=" + right)
        html += line(sp.latex(data.polynomial, symbol_names=names) + "=0")
    if sp.degree(data.polynomial, L) == 2:
        html += log_equation(a, log)
        if data.powers is not None and data.powers.image_after_log:
            prefix, html = html, ""
    else:
        html += "<p>Логарифм равен нулю тогда и только тогда, когда его аргумент равен единице. При этом аргумент положителен, а исходные знаменатели по-прежнему должны быть ненулевыми:</p>"
    for level in data.levels:
        html += trig_case(a, level)
    html += "<p>После проверки всех исходных ограничений получаем серии:</p>"
    html += "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
    return prefix or "<p>Решим уравнение по определению логарифма:</p>", html
