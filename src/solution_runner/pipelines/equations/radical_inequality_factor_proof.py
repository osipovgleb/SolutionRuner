"""Keep both parents' zero-first method over one nonnegative-factor engine."""

import hashlib

import sympy as sp

from ..probability.common import UnsupportedCondition, line
from .inequality_plan import repair
from .logarithm_rationalization_proof import choices, system
from .radical_inequality_comparison_proof import root
from .radical_inequality_factor import analyze
from .radical_inequality_factor_figures import SOURCES, chart
from .rational_inequality_division_methods import sum_text
from .rational_inequality_figures import read_formula
from .rational_inequality_methods import divisions, fraction
from .rational_inequality_parser import X, polynomial
from .rational_inequality_proof import RELATION, normalized
from .rational_substitution_preimages import comparison


def squared_quotient(a, image):
    html = "<p>Решение неравенства ищем при условиях:</p>"
    root_pole = comparison(a.denominator - 1, "=").solution
    additional = [p for p in a.constraints.excluded if p not in root_pole]
    html += system(
        [
            sp.latex(a.denominator) + r"\ge0",
            sp.latex(a.denominator) + r"\ne1",
            *(r"x\ne" + sp.latex(p) for p in additional),
        ]
    )
    html += line(choices("x", a.constraints.values))
    html += "<p>Рассмотрим два случая. Сначала числитель дроби равен нулю:</p>"
    center = -polynomial(a.numerator).nth(1) / 2
    html += line(
        root(a.numerator) + r"=1\iff\left|" + sp.latex(X - center) + r"\right|=1"
    )
    html += line(choices("x", a.zero_candidates))
    html += "<p>Учитывая исходные ограничения, в первом случае получаем:</p>" + line(
        choices("x", a.zero_case)
    )
    html += "<p>Теперь числитель дроби не равен нулю. На исходной области определения квадрат дроби строго положителен:</p>"
    factor = (
        r"\left(\frac{"
        + root(a.numerator)
        + "-1}{"
        + root(a.denominator)
        + r"-1}\right)^2"
    )
    html += line(factor + ">0")
    html += "<p>Разделив обе части неравенства на этот квадрат, получим:</p>"
    html += line(
        sp.latex(sp.apart(a.left_coefficient, X))
        + RELATION[a.operator]
        + sp.latex(a.right_coefficient)
    )
    html += "<p>Перенесём правую часть влево, приведём к общему знаменателю и разложим числитель на множители:</p>"
    html += normalized(a.stage, already_factored=True) + image
    html += "<p>Решим это неравенство методом интервалов:</p>" + line(
        choices("x", a.stage.solution)
    )
    return (
        html
        + "<p>Учитывая ограничения и первый случай, получаем множество решений исходного неравенства:</p>"
        + line(choices("x", a.solution))
    )


def common_denominator(a):
    values = divisions(a.coefficient_node)
    if (
        len(values) != 2
        or sorted(polynomial(d).degree() for _, d in values) != [1, 2]
        or any(polynomial(n).degree() > 1 for n, _ in values)
    ):
        raise UnsupportedCondition(
            "the root-factor parent needs two original fractions with affine and quadratic denominators"
        )
    denominator = sp.lcm([d for _, d in values])
    pieces = [sp.factor(n * sp.cancel(denominator / d)) for n, d in values]
    numerator = sp.Add(*pieces, evaluate=False)
    if sp.cancel(numerator / denominator - a.stage.original) != 0:
        raise UnsupportedCondition(
            "the displayed common denominator must equal the entire original coefficient"
        )
    relation = RELATION[a.operator] + "0"
    html = line(sum_text(0, values) + relation)
    html += line(sum_text(0, [(n, sp.factor(d)) for n, d in values]) + relation)
    html += line(fraction(numerator, sp.factor(denominator)) + relation)
    html += line(
        fraction(sp.factor(sp.expand(numerator)), sp.factor(denominator)) + relation
    )
    return html


def root_factor(a, image):
    html = "<p>Сначала рассмотрим случай, когда подкоренное выражение равно нулю:</p>"
    html += line(sp.latex(a.numerator) + "=0") + line(choices("x", a.zero_candidates))
    html += "<p>Проверим, при каких из этих значений исходное выражение имеет смысл. Его знаменатели требуют:</p>"
    html += system([r"x\ne" + sp.latex(p) for p in a.constraints.excluded])
    html += "<p>Поэтому решениями первого случая являются:</p>" + line(
        choices("x", a.zero_case)
    )
    html += "<p>Если подкоренное выражение строго положительно, то:</p>"
    html += line(
        sp.latex(a.numerator)
        + r">0\iff "
        + choices("x", a.constraints.roots - a.zero_candidates)
    )
    html += "<p>При этих значениях корень положителен, поэтому делим на него обе части неравенства. Приведём оставшиеся дроби к общему знаменателю:</p>"
    html += common_denominator(a)
    html += normalized(a.stage, already_factored=True)
    html += line(choices("x", a.stage.solution)) + image
    html += (
        "<p>Пересечём полученное решение с областью, где корень положителен:</p>"
        + line(choices("x", a.positive_case))
    )
    return (
        html
        + "<p>Добавляя допустимые точки первого случая, получаем множество решений исходного неравенства:</p>"
        + line(choices("x", a.solution))
    )


def build_context_repair_plan(
    context, *, parent_solution_html="", generated_solution_assets=(), method
):
    if (
        SOURCES["parents"].get(
            hashlib.sha256(parent_solution_html.encode()).hexdigest()
        )
        != method
    ):
        raise UnsupportedCondition(
            "the complete reviewed zero-first parent is required"
        )
    (_, condition, answer, solution), formula = read_formula(context)
    a = analyze(formula)
    if a.method != method:
        raise UnsupportedCondition(
            "the whole radical product must match the parent method"
        )
    image, keys, changes = chart(context, a, generated_solution_assets)
    html = (
        squared_quotient(a, image)
        if method == "squared_quotient"
        else root_factor(a, image)
    )
    return repair(
        condition, answer, solution, a.answer, html, keys=keys, asset_changes=changes
    )
