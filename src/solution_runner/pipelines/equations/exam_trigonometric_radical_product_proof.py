"""Explain both product-zero cases without cancelling an admissible zero radical."""

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S, T, U
from .exam_trigonometric_inverse import angles, compare_q


def homogeneous_domain(radicand):
    if radicand.free_symbols != {S, C} or sp.fraction(radicand)[1].free_symbols:
        return ""
    from .exam_trigonometric_linear_phase import branch
    from .exam_trigonometric_proof import formula, pi

    amplitude = sp.sqrt(sp.simplify(radicand.coeff(S) ** 2 + radicand.coeff(C) ** 2))
    shifted = branch(radicand - amplitude)
    if shifted is None:
        raise UnsupportedCondition(
            "the linear radical domain needs a reviewed exact phase"
        )
    phase = shifted.angle_shift
    argument = sp.Symbol("x", real=True) + phase * sp.pi
    html = "<p>Решим исходное неравенство по формуле синуса суммы. Его коэффициент положителен, а синус неотрицателен на отрезках от 0 до π с периодом 2π:</p>"
    html += line(
        formula(radicand)
        + "="
        + sp.latex(amplitude)
        + r"\sin\left("
        + sp.latex(argument)
        + r"\right)"
    )
    html += line(
        pi(-phase)
        + r"+2\pi n\le x\le "
        + pi(1 - phase)
        + r"+2\pi n,\quad n\in\mathbb Z"
    )
    return html


def affine_ratio(radicand):
    denominator = sp.fraction(radicand)[1]
    if denominator.free_symbols not in ({S}, {C}):
        return None
    variable = T if denominator.has(C) else U
    value = sp.cancel(
        radicand.subs(S, T * C) if variable == T else radicand.subs(C, U * S)
    )
    if value.free_symbols != {variable} or sp.degree(value, variable) != 1:
        return None
    coefficient, constant = value.coeff(variable), value.subs(variable, 0)
    return (variable, coefficient, constant) if constant != 0 else None


def accepted_ratio(a, q, ratio):
    from .exam_trigonometric_proof import formula, pi

    variable, _, _ = ratio
    sine, cosine = sp.sin(q * sp.pi), sp.cos(q * sp.pi)
    value = sp.simplify(sine / cosine if variable == T else cosine / sine)
    radicand = sp.simplify(a.radical_product.radicand.subs({S: sine, C: cosine}))
    if compare(radicand, sp.S.Zero) <= 0:
        raise UnsupportedCondition(
            "the accepted ratio branch must have a positive radical"
        )
    q = q - 2 if compare_q(q, sp.S.One) > 0 else q
    function = r"\tg" if variable == T else r"\ctg"
    expression = (
        function
        + r"\left("
        + pi(q)
        + r"+2\pi k\right)="
        + function
        + r"\left("
        + pi(q)
        + r"\right)"
    )
    if compare_q(q, sp.S.Zero) < 0:
        expression += "=-" + function + r"\left(" + pi(-q) + r"\right)"
    html = "<p>Проверим оставшуюся серию, используя периодичность и нечётность тригонометрического отношения:</p>"
    html += line(expression + "=" + sp.latex(value))
    return html + line(
        formula(a.radical_product.radicand) + "=" + sp.latex(radicand) + ">0"
    )


def positive_case(a, positive, ratio):
    from .exam_trigonometric_proof import formula, pi, polynomial
    from .exam_trigonometric_radical_product import factor_branches

    data = a.radical_product
    original = factor_branches(data.factor, a.preferred, a.allow_inverse)
    domain = homogeneous_domain(data.radicand)
    html = (
        "".join(
            polynomial(
                branch,
                allowed_residues=None if domain or ratio else filtered.residues,
                factorization=True,
            )
            for branch, filtered in zip(original, positive)
        )
        + domain
    )
    for branch, filtered in zip(original, positive):
        for value in branch.values:
            for q in angles(branch.variable, value, a.allow_inverse):
                if q in filtered.residues:
                    if ratio:
                        html += accepted_ratio(a, q, ratio)
                    continue
                substitution = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
                forbidden = any(sp.simplify(p.subs(substitution)) == 0 for p in a.poles)
                html += line("x=" + pi(q) + r"+2\pi k")
                if forbidden:
                    html += (
                        "<p>Исходный знаменатель равен нулю; эта серия недопустима.</p>"
                    )
                    continue
                radicand = sp.simplify(data.radicand.subs(substitution))
                if compare(radicand, sp.S.Zero) == 0:
                    html += "<p>Здесь подкоренное выражение равно нулю. Эти корни уже рассмотрены в первом случае и не относятся к случаю положительного радикала.</p>"
                else:
                    if compare(radicand, sp.S.Zero) >= 0:
                        raise UnsupportedCondition(
                            "a rejected product branch must violate its original domain"
                        )
                    html += line(
                        formula(data.radicand) + "=" + sp.latex(radicand) + "<0"
                    )
                    html += "<p>Корень не определён; серию исключаем.</p>"
    return html


def proof(a):
    from .exam_trigonometric_proof import families, formula, polynomial
    from .exam_trigonometric_radical_product import cases

    data = a.radical_product
    zero, positive = cases(a, a.preferred, a.allow_inverse)
    root_num = sp.fraction(data.radicand)[0]
    html = line(a.original)
    html += "<p>Запишем область определения до преобразований:</p>"
    for pole in a.poles:
        html += line(formula(pole) + r"\ne0")
    html += line(formula(data.radicand) + r"\ge0")
    ratio = affine_ratio(data.radicand)
    if ratio:
        variable, coefficient, constant = ratio
        html += line(
            formula(variable)
            + (r"\ge " if compare(coefficient, sp.S.Zero) > 0 else r"\le ")
            + sp.latex(sp.simplify(-constant / coefficient))
        )
    if sp.fraction(data.radicand)[1].free_symbols:
        html += "<p>На исходной области определения квадрат знаменателя положителен. Умножим неравенство на этот квадрат:</p>"
        html += line(formula(a.domain) + r"\ge0")
    if any(b.residues for b in zero):
        html += "<p>Рассмотрим два случая. Сначала подкоренное выражение равно нулю. При сохранении исходных знаменателей это сразу даёт нулевое произведение:</p>"
        html += line(formula(data.radicand) + "=0")
        for branch in zero:
            html += polynomial(branch, allowed_residues=branch.residues)
        html += "<p>Теперь подкоренное выражение положительно. Корень ненулевой, поэтому равен нулю первый множитель:</p>"
    else:
        html += "<p>Нулевое подкоренное выражение обращает исходный знаменатель в нуль и запрещено. Поэтому корень строго положителен; нулю должен равняться первый множитель:</p>"
        html += line(formula(root_num) + r"=0\quad\text{не допускается}")
    html += line(formula(data.radicand) + ">0")
    html += line(formula(data.factor) + "=0")
    if data.factor.has(S, C):
        html += line(r"\sin^2x+\cos^2x=1")
    html += positive_case(a, positive, ratio)
    html += "<p>Объединим допустимые серии обоих случаев:</p>"
    html += "".join(line(text + r",\quad k\in\mathbb Z") for text in families(a))
    return "<p>Решим уравнение с сохранением исходной области определения:</p>", html
