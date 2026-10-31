"""Keep the parent's identities, full square and exact circle selection in order."""

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exam_exponential_proof import n
from .exam_trigonometric import C, S, periodic, table

K = sp.Symbol("k", integer=True)


def formula(value):
    return sp.latex(value, symbol_names={S: r"(\sin x)", C: r"(\cos x)"})


def pi(q):
    return sp.latex(q * sp.pi)


def series_lines(series):
    remaining = list(series)
    result = []
    while remaining:
        offset, period = remaining.pop(0)
        pair = next(
            ((a, p) for a, p in remaining if p == period and a + offset == period), None
        )
        if pair:
            remaining.remove(pair)
            angle = min(offset, pair[0])
            result.append(
                "x=" + r"\pm" + pi(angle) + "+" + sp.latex(period * sp.pi * K)
            )
        else:
            result.append("x=" + sp.latex(offset * sp.pi + period * sp.pi * K))
    return tuple(result)


def families(a):
    if (
        a.alternating
        and len(a.branches) == 1
        and a.branches[0].variable == S
        and len(a.branches[0].values) > 1
    ):
        result = []
        for value in a.branches[0].values:
            if value == 0:
                result.append(r"x=\pi k")
            else:
                residues = table(S, value)
                angle = next(
                    q if q <= sp.Rational(1, 2) else q - 2
                    for q in residues
                    if q <= sp.Rational(1, 2) or q >= sp.Rational(3, 2)
                )
                result.append(r"x=(-1)^k\cdot" + pi(angle) + r"+\pi k")
        return tuple(result)
    return series_lines(a.series)


def polynomial(branch):
    p = branch.polynomial
    variable = branch.variable
    html = line(formula(p) + "=0")
    degree = sp.Poly(p, variable).degree()
    if degree == 2:
        A, B, D0 = sp.Poly(p, variable).all_coeffs()
        html += line(
            "D=("
            + n(B)
            + r")^2-4\cdot("
            + n(A)
            + r")\cdot("
            + n(D0)
            + ")="
            + n(sp.simplify(B * B - 4 * A * D0))
        )
    elif degree > 2:
        html += line(formula(sp.factor(p)) + "=0")
        for factor, _ in sp.factor_list(p, variable, extension=True)[1]:
            poly = sp.Poly(factor, variable)
            if poly.degree() == 2:
                A, B, D0 = poly.all_coeffs()
                d = sp.simplify(B * B - 4 * A * D0)
                if d < 0:
                    html += line(formula(factor) + ">0")
                    html += "<p>Квадратный множитель имеет положительный старший коэффициент и отрицательный дискриминант, поэтому не обращается в нуль.</p>"
    for value in branch.candidates:
        html += line(formula(variable) + "=" + sp.latex(value))
        if value not in branch.values:
            html += "<p>Это значение не входит в отрезок от −1 до 1, поэтому соответствующее тригонометрическое уравнение корней не имеет.</p>"
        else:
            for text in series_lines(periodic(table(variable, value))):
                html += line(text + r",\quad k\in\mathbb Z")
    return html


def first(a):
    intro = "<p>Преобразуем уравнение с помощью формул приведения и двойного угла:</p>"
    html = ""
    for text, value in a.identities:
        html += line(text + "=" + formula(value))
    html += line(formula(a.raw) + "=0")
    if a.raw != a.reduced:
        other = S if a.preferred == C else C
        html += "<p>Выразим квадрат второй функции через квадрат первой:</p>"
        html += line(formula(other**2) + "=" + formula(1 - a.preferred**2))
        html += line(formula(a.reduced) + "=0")
    factorization = sp.factor(a.reduced)
    factors = sp.factor_list(a.reduced, S, C)[1]
    full_square = len(factors) == 1 and factors[0][1] == 2
    if a.square:
        html += (
            "<p>Выделим полный квадрат:</p>"
            if full_square
            else "<p>После приведения левая часть этой задачи не является полным квадратом. Разложим многочлен четвёртой степени на множители:</p>"
        )
        html += line(formula(factorization) + "=0")
    elif len(a.branches) > 1:
        html += "<p>Произведение равно нулю, когда хотя бы один множитель равен нулю. На тригонометрический множитель не делим, чтобы сохранить все ветви:</p>"
        html += line(formula(sp.factor(a.raw)) + "=0")
    html += line(r"-1\le\sin x\le1,\quad-1\le\cos x\le1")
    for branch in a.branches:
        html += polynomial(branch)
    if any(sp.Poly(b.polynomial, b.variable).degree() > 1 for b in a.branches):
        html += "<p>Объединим полученные серии, учитывая периодичность:</p>"
        for text in families(a):
            html += line(text + r",\quad k\in\mathbb Z")
    return intro, html


def render(a, image):
    intro, steps = first(a)
    before = image if a.image_position == "before-intro" else ""
    after = image if a.image_position == "after-intro" else ""
    first_html = before + intro + after + steps
    second = (
        "<p>С помощью числовой окружности отберём корни, принадлежащие промежутку "
        + inline(a.interval)
        + ". Границы дуги учитываем в соответствии с квадратными и круглыми скобками:</p>"
    )
    lo, hi, lc, uc = a.bounds
    for root in a.selected:
        second += line(
            pi(lo)
            + (r"\le" if lc else "<")
            + pi(root)
            + (r"\le" if uc else "<")
            + pi(hi)
        )
    if not a.selected:
        second += "<p>На указанной дуге точек решения нет.</p>"
    html = (
        (image if a.image_position == "outside" else "")
        + '<ol data-layout="source-subparts" type="a"><li data-list-marker="а)">'
        + first_html
        + '</li><li data-list-marker="б)">'
        + second
        + "</li></ol>"
    )
    all_roots = (
        r";\ ".join(families(a)) + r",\ k\in\mathbb Z" if a.series else r"\varnothing"
    )
    selected = r";\ ".join(pi(q) for q in a.selected) or r"\varnothing"
    return (
        "а) " + all_roots + "; б) " + selected,
        "<p>а) " + inline(all_roots) + "; б) " + inline(selected) + ".</p>",
        html,
    )
