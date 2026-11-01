"""Explain both product-zero cases without cancelling an admissible zero radical."""

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_inverse import angles


def proof(a):
    from .exam_trigonometric import solve_branches
    from .exam_trigonometric_proof import families, formula, pi, polynomial
    from .exam_trigonometric_radical_product import cases

    data = a.radical_product
    zero, positive = cases(a, a.preferred, a.allow_inverse)
    root_num = sp.fraction(data.radicand)[0]
    html = line(a.original)
    html += "<p>Запишем область определения до преобразований:</p>"
    for pole in a.poles:
        html += line(formula(pole) + r"\ne0")
    html += line(formula(data.radicand) + r"\ge0")
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
    original = solve_branches(data.factor, a.preferred, a.allow_inverse)[1]
    for branch, filtered in zip(original, positive):
        html += polynomial(
            branch, allowed_residues=filtered.residues, factorization=True
        )
        for value in branch.values:
            for q in angles(branch.variable, value, a.allow_inverse):
                if q in filtered.residues:
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
    html += "<p>Объединим допустимые серии обоих случаев:</p>"
    html += "".join(line(text + r",\quad k\in\mathbb Z") for text in families(a))
    return "<p>Решим уравнение с сохранением исходной области определения:</p>", html
