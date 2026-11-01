"""Keep the parent's identities, full square and exact circle selection in order."""

from dataclasses import replace
from functools import cmp_to_key

import sympy as sp

from ..probability.common import line
from ..word_problems.water_season_proof import inline
from .exam_exponential_proof import n
from .exam_trigonometric import C, S, T, U, periodic, table
from .exam_trigonometric_inverse import compare_q, level_series
from .exam_trigonometric_inverse import display_angle as complementary_angle
from .exam_trigonometric_proof_methods import method_proof
from .exam_trigonometric_variants import (
    all_root_answer,
    method_notes,
    root_notation,
    selection_notes,
)

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


def pi(q, *, sine_inverse=False):
    angle = sp.expand(q * sp.pi)
    return sp.latex(
        complementary_angle(angle) if sine_inverse else angle, inv_trig_style="full"
    )


def series_lines(series, *, sine_inverse=False):
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
            text = pi(angle, sine_inverse=sine_inverse)
            if sp.expand(angle * sp.pi).is_Add:
                text = r"\left(" + text + r"\right)"
            result.append("x=" + r"\pm" + text + "+" + sp.latex(period * sp.pi * K))
        else:
            result.append(
                "x="
                + sp.latex(
                    sp.expand(
                        (
                            complementary_angle(sp.expand(offset * sp.pi))
                            if sine_inverse
                            else offset * sp.pi
                        )
                        + period * sp.pi * K
                    ),
                    inv_trig_style="full",
                )
            )
    return tuple(result)


def families(a):
    if a.signed_series:
        return series_lines(a.signed_series)
    if a.restricted_families:
        from .exam_trigonometric_restricted_families import formulas

        return formulas(a)
    if a.family_parameters and len(set(a.family_parameters)) > 1:
        return tuple(
            text.replace("k", name)
            for item, name in zip(a.series, a.family_parameters)
            for text in series_lines((item,), sine_inverse=a.sine_inverse)
        )
    if a.square_difference is not None:
        return tuple(
            text.replace("k", a.square_difference.parameter)
            for text in series_lines(a.series)
        )
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
    return series_lines(a.series, sine_inverse=a.sine_inverse)


def polynomial(
    branch,
    substitution=None,
    allow_inverse=False,
    factorization=False,
    allowed_residues=None,
    angle="x",
    root_scale=sp.S.One,
    sine_inverse=False,
):
    if branch.angle_shift:
        from .exam_trigonometric_linear_phase import proof

        return proof(branch, angle, root_scale, allowed_residues)
    p = branch.polynomial
    variable = branch.variable
    symbol = sp.Symbol(substitution, real=True) if substitution else variable
    from .exam_trigonometric_ratios import linear_proof

    html = linear_proof(branch, angle) + line(
        formula(p.subs(variable, symbol), angle) + "=0"
    )
    degree = sp.Poly(p, variable).degree()
    if branch.square_level:
        level = sp.simplify(-p.subs(variable, 0) / p.coeff(variable, 2))
        html += "<p>Выразим квадрат функции:</p>" + line(
            formula(symbol**2, angle) + "=" + sp.latex(level)
        )
    elif branch.square_factor:
        from .exam_trigonometric_square_factor import polynomial_proof

        html += polynomial_proof(branch, symbol, angle)
    elif degree == 2 and factorization:
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
        if branch.grouping:
            from .exam_trigonometric_cubic import grouped

            html += grouped(p, variable, symbol, angle, branch.quadratic_common)
        else:
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
        branch,
        substitution,
        allow_inverse,
        allowed_residues,
        angle,
        root_scale,
        sine_inverse=sine_inverse,
    )


def candidate_lines(
    branch,
    substitution=None,
    allow_inverse=False,
    allowed_residues=None,
    angle="x",
    root_scale=sp.S.One,
    sine_inverse=False,
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
                from .exam_trigonometric_inverse import angles

                if variable in (T, U) or (
                    allow_inverse
                    and any(
                        q.is_Rational is not True for q in angles(variable, value, True)
                    )
                ):
                    from .exam_trigonometric_selection import restricted_series

                    series = restricted_series(
                        replace(branch, residues=tuple(allowed_residues)), value
                    )
                else:
                    series = periodic(
                        set(allowed_residues) & set(table(variable, value))
                    )
            for text in series_lines(
                tuple((q / root_scale, p / root_scale) for q, p in series),
                sine_inverse=sine_inverse,
            ):
                html += line(text + r",\quad k\in\mathbb Z")
    return html


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
        if any(b.square_factor for b in a.branches):
            intro = (
                "<p>Сделаем замену переменной и разложим многочлен на множители:</p>"
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
            html += polynomial(
                branch, a.substitution, a.allow_inverse, sine_inverse=a.sine_inverse
            )
        return intro, html
    for text, value in a.identities:
        html += line(text + "=" + formula(value))
    if a.factored_source is not None:
        html += line(formula(a.factored_source) + "=0")
        html += line(formula(S * S + C * C) + "=1")
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
        html += line(formula(sp.factor(a.reduced, extension=True)) + "=0")
    html += line(r"-1\le\sin x\le1,\quad-1\le\cos x\le1")
    for branch in a.branches:
        html += polynomial(
            branch,
            allow_inverse=a.allow_inverse,
            factorization=a.factorization,
            sine_inverse=a.sine_inverse,
        )
    if any(sp.Poly(b.polynomial, b.variable).degree() > 1 for b in a.branches):
        html += "<p>Объединим полученные серии, учитывая периодичность:</p>"
        for text in families(a):
            html += line(text + r",\quad k\in\mathbb Z")
    return intro, html


def inequality_selection(a):
    from .exam_trigonometric_inequalities import inequality_selection as select

    return select(a)


def render(a, image):
    system_image = ""
    if a.auxiliary_notes:
        image, system_image = image
    selection_image = image
    if a.log_product is not None and isinstance(image, tuple):
        image, selection_image = image
    intro, steps = first(a)
    if a.single_part:
        from .exam_trigonometric_single import render as render_single

        return render_single(a, image, intro, steps)
    before = image if a.image_position == "before-intro" else ""
    after = image if a.image_position == "after-intro" else ""
    first_html = (
        before
        + intro
        + after
        + steps
        + (image if a.image_position == "after-steps" else "")
    )
    if (
        a.log_product is not None
        and selection_image != image
        and a.log_product.selection_image_position == "after-steps"
    ):
        first_html += selection_image
    from .exam_trigonometric_affine_proof import selection as number_line_selection
    from .exam_trigonometric_neighbors import proof as neighbor_selection
    from .exam_trigonometric_selection import progressions

    selectors = {
        "neighbors": neighbor_selection,
        "number_line": number_line_selection,
        "inequalities": inequality_selection,
        "progressions": progressions,
    }
    if a.global_radical is not None:
        from .exam_trigonometric_global_radical_proof import selection

        second = selection(a)
    elif a.log_polynomial is not None and a.log_polynomial.alternative_selection:
        from .exam_trigonometric_log_selection import selection

        second = selection(a, image)
    elif a.bounded_log is not None:
        from .exam_trigonometric_bounded_log_proof import selection

        second = selection(a)
    elif (
        a.radical_equation is not None
        and a.radical_equation.kind == "half_tangent"
        and any(b.is_Rational is not True for b in a.bounds[:2])
    ):
        from .exam_trigonometric_radical_proof import numeric_selection

        second = numeric_selection(a)
    elif a.selection_method in selectors:
        second = selectors[a.selection_method](a)
    else:
        from .exam_trigonometric_circle import selection_proof

        second = selection_proof(a, selection_image, paired=selection_image != image)
    second += selection_notes(a, system_image)
    html = (
        (image if a.image_position == "outside" else "")
        + '<ol data-layout="source-subparts" type="a"><li data-list-marker="а)">'
        + first_html
        + '</li><li data-list-marker="б)">'
        + second
        + "</li></ol>"
    )
    html += method_notes(a)
    all_roots = all_root_answer(a)
    selected = (
        r";\ ".join(pi(q, sine_inverse=a.sine_inverse) for q in a.selected)
        or r"\varnothing"
    )
    return root_notation(
        a,
        (
            "а) " + all_roots + "; б) " + selected,
            "<p>а) " + inline(all_roots) + "; б) " + inline(selected) + ".</p>",
            html,
        ),
    )
