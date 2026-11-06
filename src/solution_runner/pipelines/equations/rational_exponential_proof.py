"""Keep the parent's substitution, common denominator, signs and inverse order."""

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from ..word_problems.water_season_proof import inline
from .exponential_inequality_preimage_proof import alternatives
from .exponential_inequality_proof import power
from .exponential_inequality_quadratic import inverse
from .exponential_inequality_quadratic_labels import level_text
from .exponential_inequality_quadratic_proof import expression
from .exponential_inequality_reduction_proof import sum_terms
from .rational_exponential_input import monomial
from .rational_inequality_factor_methods import positive_quadratics
from .rational_inequality_methods import fraction, terms
from .rational_inequality_parser import X
from .rational_inequality_proof import RELATION, interval_signs_text, normalized
from .rational_substitution_preimages import bounds


def common_fraction(stage):
    pieces = []
    for sign, node in terms(stage.left) + terms(stage.right, -1):
        numerator, denominator = sp.fraction(sp.cancel(node.value))
        if numerator != 0:
            pieces.append((sign * numerator, denominator))
    denominator = sp.lcm([d for _, d in pieces]) if pieces else sp.Integer(1)
    numerator = sp.Add(
        *(
            n
            if denominator == d
            else sp.Mul(n, sp.factor(sp.cancel(denominator / d)), evaluate=False)
            for n, d in pieces
        ),
        evaluate=False,
    )
    if sp.cancel(numerator / denominator - stage.original) != 0:
        raise UnsupportedCondition(
            "the displayed common denominator must preserve the full expression"
        )
    return numerator, sp.factor(denominator)


def parts(solution):
    if solution == sp.EmptySet:
        return ()
    values = solution.args if isinstance(solution, sp.Union) else (solution,)
    values = tuple(
        singleton
        for part in values
        for singleton in (
            tuple(sp.FiniteSet(p) for p in part)
            if isinstance(part, sp.FiniteSet)
            else (part,)
        )
    )
    return tuple(
        sorted(values, key=lambda v: v.start if isinstance(v, sp.Interval) else min(v))
    )


def display_side(node, variable):
    pieces = []
    for sign, item in terms(node):
        text = (
            fraction(*(c.value for c in item.children))
            if item.kind == "divide"
            else sp.latex(item.value)
        )
        pieces.append((sign, text.replace("x", variable)))
    return sum_terms(pieces)


def algebra(a, variable):
    stage = a.stage
    numerator, denominator = common_fraction(stage)
    html = "<p>Перенесём правую часть влево и приведём к общему знаменателю на исходной области определения:</p>"
    html += line(
        fraction(numerator, denominator).replace("x", variable)
        + RELATION[a.operator]
        + "0"
    )
    html += line(
        fraction(sp.expand(numerator), denominator).replace("x", variable)
        + RELATION[a.operator]
        + "0"
    )
    n = sp.fraction(stage.expression)[0]
    if stage.original != stage.expression or stage.holes or sp.factor(n) != n:
        html += named_normalized(stage, variable)
    for factor, completed in positive_quadratics(stage):
        html += "<p>Этот квадратный множитель положителен при всех действительных значениях замены:</p>"
        left, right = expression(factor, variable), expression(completed, variable)
        html += line(left + ("=" + right if right != left else "") + ">0")
    html += "<p>Применим метод интервалов, сохраняя все нули числителя и исключённые точки:</p>"
    if any(isinstance(p, sp.FiniteSet) for p in parts(a.positive_solution)):
        html += "<p>Допустимые нули числителя дают отдельные решения; не делим на обнуляющийся множитель:</p>"
    html += line(interval_signs_text(stage).replace("x", variable))
    return html + line(alternatives(variable, stage.solution))


def named_normalized(stage, variable):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(normalized(stage), "html.parser")
    for span in soup.find_all(attrs={"data-inline-latex": True}):
        span["data-inline-latex"] = span["data-inline-latex"].replace("x", variable)
    return str(soup)


def return_branch(a, values, variable):
    mapping = {t: roots[0] for t, _, roots in a.back}
    back = {t: value for t, value, _ in a.back}
    actual = power(a.base, a.exponent)
    grows = sp.diff(a.exponent, X) > 0
    html = "<p>При " + inline(alternatives(variable, values)) + " получаем:</p>"
    for t, op in bounds(values):
        if t == 0 and op == ">":
            continue
        relation = "=" if op == "=" else RELATION[op]
        html += line(
            actual
            + relation
            + sp.latex(t)
            + r"\iff "
            + sp.latex(a.exponent)
            + relation
            + " "
            + level_text(a.base, t, back[t])
        )
    solution = inverse(values, mapping, grows).intersect(a.domain)
    return html + line(alternatives("x", solution, a.endpoint))


def render(a, variable, image=""):
    html = line(a.formula)
    if a.extra_poles:
        html += "<p>Сохраним исходные ограничения показателей:</p>"
        html += line(r",\quad ".join("x\\ne " + sp.latex(p) for p in a.extra_poles))
    html += "<p>Сделаем замену. Показательная функция положительна:</p>"
    html += line(variable + "=" + power(a.base, a.exponent) + ">0")
    seen = {a.base**a.exponent}
    for node in a.powers:
        if node.value not in seen:
            seen.add(node.value)
            b, g = (c.value for c in node.children)
            html += line(
                power(b, g)
                + "="
                + expression(monomial(b, g, a.base, a.exponent), variable)
            )
    if a.stage.poles:
        html += "<p>Исходные знаменатели должны быть ненулевыми:</p>"
        html += line(
            r",\quad ".join(variable + r"\ne " + sp.latex(p) for p in a.stage.poles)
        )
    html += "<p>Тогда неравенство принимает вид:</p>"
    html += line(
        display_side(a.stage.left, variable)
        + RELATION[a.operator]
        + display_side(a.stage.right, variable)
    )
    html += algebra(a, variable) + image
    if a.positive_solution != a.stage.solution:
        html += "<p>Учитываем положительность замены. Отрицательные значения и нуль не могут быть значениями показательной функции:</p>"
        html += line(alternatives(variable, a.positive_solution))
    html += (
        "<p>Вернёмся к исходной переменной. Основание "
        + inline(sp.latex(a.base) + ">1")
        + ", поэтому при сравнении степеней сравниваем показатели."
        + (
            " При делении на отрицательный коэффициент показателя знак меняется:"
            if sp.diff(a.exponent, X) < 0
            else ":"
        )
        + "</p>"
    )
    for values in parts(a.positive_solution):
        html += return_branch(a, values, variable)
    return (
        html
        + "<p>Объединяя допустимые решения, получаем:</p>"
        + line(r"x\in " + a.answer)
    )
