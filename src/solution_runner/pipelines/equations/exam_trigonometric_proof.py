"""Keep the parent's identities, full square and exact circle selection in order."""

from functools import cmp_to_key

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exam_exponential_proof import n
from .exam_trigonometric import C, S, T, U, periodic, table
from .exam_trigonometric_inverse import compare_q, level_series

K = sp.Symbol("k", integer=True)


def formula(value, angle="x"):
    return sp.latex(
        value,
        symbol_names={
            S: r"(\sin " + angle + ")",
            C: r"(\cos " + angle + ")",
            T: r"(\tg " + angle + ")",
            U: r"(\ctg " + angle + ")",
        },
    )


def pi(q):
    return sp.latex(sp.expand(q * sp.pi), inv_trig_style="full")


def series_lines(series):
    remaining = list(series)
    result = []
    while remaining:
        offset, period = remaining.pop(0)
        pair = next(
            (
                (a, p)
                for a, p in remaining
                if p == period and (a + offset == period or a + offset == 0)
            ),
            None,
        )
        if pair:
            remaining.remove(pair)
            angle = min((abs(offset), abs(pair[0])), key=cmp_to_key(compare_q))
            text = pi(angle)
            if sp.expand(angle * sp.pi).is_Add:
                text = r"\left(" + text + r"\right)"
            result.append("x=" + r"\pm" + text + "+" + sp.latex(period * sp.pi * K))
        else:
            result.append(
                "x="
                + sp.latex(
                    sp.expand(offset * sp.pi + period * sp.pi * K),
                    inv_trig_style="full",
                )
            )
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


def polynomial(
    branch,
    substitution=None,
    allow_inverse=False,
    factorization=False,
    allowed_residues=None,
    angle="x",
    root_scale=sp.S.One,
):
    p = branch.polynomial
    variable = branch.variable
    symbol = sp.Symbol(substitution, real=True) if substitution else variable
    from .exam_trigonometric_ratios import linear_proof

    html = linear_proof(branch, angle) + line(
        formula(p.subs(variable, symbol), angle) + "=0"
    )
    degree = sp.Poly(p, variable).degree()
    if degree == 2 and factorization:
        html += (
            "<p>Вынесем общий множитель. Произведение равно нулю, когда хотя бы один множитель равен нулю; на тригонометрический множитель не делим:</p>"
            if p.subs(variable, 0) == 0
            else "<p>Разложим квадратный трёхчлен на множители. Произведение равно нулю, когда хотя бы один множитель равен нулю:</p>"
        )
        factored = (
            sp.factor(p) if p.subs(variable, 0) == 0 else sp.factor(p, extension=True)
        )
        html += line(formula(factored.subs(variable, symbol), angle) + "=0")
    elif degree == 2:
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
        html += line(formula(sp.factor(p), angle) + "=0")
        for factor, _ in sp.factor_list(p, variable, extension=True)[1]:
            poly = sp.Poly(factor, variable)
            if poly.degree() == 2:
                A, B, D0 = poly.all_coeffs()
                d = sp.simplify(B * B - 4 * A * D0)
                if d < 0:
                    html += line(formula(factor, angle) + ">0")
                    html += "<p>Квадратный множитель имеет положительный старший коэффициент и отрицательный дискриминант, поэтому не обращается в нуль.</p>"
    return html + candidate_lines(
        branch, substitution, allow_inverse, allowed_residues, angle, root_scale
    )


def candidate_lines(
    branch,
    substitution=None,
    allow_inverse=False,
    allowed_residues=None,
    angle="x",
    root_scale=sp.S.One,
):
    variable = branch.variable
    symbol = sp.Symbol(substitution, real=True) if substitution else variable
    html = ""
    for value in branch.candidates:
        html += line(formula(symbol, angle) + "=" + sp.latex(value))
        if substitution and value in branch.values:
            html += "<p>Вернёмся к исходной переменной:</p>"
            html += line(formula(variable, angle) + "=" + sp.latex(value))
        if value in branch.excluded:
            html += "<p>Это значение нарушает область определения исходного уравнения, поэтому соответствующая ветвь исключается.</p>"
        elif value not in branch.values:
            html += "<p>Это значение не входит в отрезок от −1 до 1, поэтому соответствующее тригонометрическое уравнение корней не имеет.</p>"
        else:
            series = level_series(variable, value, allow_inverse)
            if allowed_residues is not None:
                series = periodic(set(allowed_residues) & set(table(variable, value)))
            for text in series_lines(
                tuple((q / root_scale, p / root_scale) for q, p in series)
            ):
                html += line(text + r",\quad k\in\mathbb Z")
    return html


def method_proof(a):
    if any(b.impossible for b in a.branches):
        from .exam_trigonometric_combination import proof

        return proof(a)
    if a.absolute is not None:
        from .exam_trigonometric_absolute import proof

        return proof(a)
    if a.translation:
        from .exam_trigonometric_translation import proof

        return proof(a)
    if a.strict_domain:
        from .exam_trigonometric_radical_quotient import proof

        return proof(a)
    if a.fraction is not None:
        from .exam_trigonometric_rational import proof

        return proof(a)
    if a.domain is not None:
        from .exam_trigonometric_domain import proof

        return proof(a)
    if a.preferred == T:
        from .exam_trigonometric_ratios import tangent_proof

        return tangent_proof(a)
    if a.poles and a.reciprocal is None:
        from .exam_trigonometric_poles import proof

        return proof(a)
    if a.scale != 1 or a.reciprocal is not None or a.division:
        from .exam_trigonometric_variants import proof

        return proof(a)
    if a.preferred == U:
        from .exam_trigonometric_ratios import cotangent_proof

        return cotangent_proof(a)
    return None


def first(a):
    selected = method_proof(a)
    if selected is not None:
        return selected
    intro = "<p>Преобразуем уравнение с помощью формул приведения и двойного угла:</p>"
    html = ""
    if a.substitution:
        intro = (
            "<p>Сделаем замену переменной и решим полученное квадратное уравнение:</p>"
        )
        for text, value in a.identities:
            if value in (S, C):
                continue
            other = S if a.preferred == C else C
            html += line(text + "=" + formula(sp.rem(value, S * S + C * C - 1, other)))
        for branch in a.branches:
            html += "<p>Введём обозначение:</p>" + line(
                a.substitution + "=" + formula(branch.variable)
            )
            html += line("-1\\le " + a.substitution + "\\le1")
            if len(a.branches) == 1 and sp.expand(a.reduced - branch.polynomial) != 0:
                html += line(
                    formula(
                        a.reduced.subs(
                            branch.variable, sp.Symbol(a.substitution, real=True)
                        )
                    )
                    + "=0"
                )
            html += polynomial(branch, a.substitution, a.allow_inverse)
        return intro, html
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
        html += polynomial(
            branch,
            allow_inverse=a.allow_inverse,
            factorization=a.factorization,
        )
    if any(sp.Poly(b.polynomial, b.variable).degree() > 1 for b in a.branches):
        html += "<p>Объединим полученные серии, учитывая периодичность:</p>"
        for text in families(a):
            html += line(text + r",\quad k\in\mathbb Z")
    return intro, html


def inequality_selection(a):
    html = (
        "<p>Найдём корни на промежутке "
        + inline(a.interval)
        + ". Решим неравенства для целого параметра каждой серии:</p>"
    )
    inverse = (
        set().union(*(q.atoms(sp.acos) for q in a.residues)) if a.residues else set()
    )
    for angle in inverse:
        html += (
            "<p>Для главного значения арккосинуса используем его область значений:</p>"
        )
        html += line("0<" + sp.latex(angle, inv_trig_style="full") + r"<\pi")
    lo, hi, lc, uc = a.bounds
    for offset, period, start, end, values in a.selections:
        html += line(
            pi(lo)
            + (r"\le" if lc else "<")
            + sp.latex(
                sp.expand(offset * sp.pi + period * sp.pi * K), inv_trig_style="full"
            )
            + (r"\le" if uc else "<")
            + pi(hi)
        )
        html += line(
            sp.latex(sp.simplify((lo - offset) / period), inv_trig_style="full")
            + (r"\le" if lc else "<")
            + "k"
            + (r"\le" if uc else "<")
            + sp.latex(sp.simplify((hi - offset) / period), inv_trig_style="full")
        )
        if start > end:
            html += "<p>Подходящих целых значений k нет.</p>"
        else:
            html += line(
                r"k\in\{" + ";".join(str(k) for k in range(start, end + 1)) + r"\}"
            )
            for root in values:
                html += line("x=" + pi(root))
    return html


def render(a, image):
    intro, steps = first(a)
    before = image if a.image_position == "before-intro" else ""
    after = image if a.image_position == "after-intro" else ""
    first_html = (
        before
        + intro
        + after
        + steps
        + (image if a.image_position == "after-steps" else "")
    )
    if a.selection_method == "inequalities":
        second = inequality_selection(a)
    elif a.selection_method == "progressions":
        from .exam_trigonometric_selection import progressions

        second = progressions(a)
    else:
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
    if a.alternative is not None:
        alternative_intro, alternative_steps = first(a.alternative)
        html += (
            "<p><b>Приведём другое решение пункта а).</b></p>"
            + alternative_intro
            + alternative_steps
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
