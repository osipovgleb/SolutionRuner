"""Keep positive-factor cancellation before the parent's trigonometric algebra."""

from dataclasses import replace

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S


def power(base, exponent):
    from .exam_trigonometric_proof import formula

    if exponent == 0:
        return "1"
    return r"\left(" + sp.latex(base) + r"\right)^{" + formula(exponent) + "}"


def product(primes):
    return r"\cdot".join(power(p, e) for p, e in primes if e != 0) or "1"


def exponent_steps(a, left, right):
    from .exam_trigonometric_proof import formula

    data = a.power_equality
    if data.equal_powers is not None:
        base, first, second = data.equal_powers
        html = line(power(base, first) + "=" + power(base, second))
        html += line(sp.latex(base) + r">0,\quad " + sp.latex(base) + r"\ne1")
        html += "<p>У положительных степеней с одинаковым основанием, отличным от единицы, равны показатели:</p>"
        return html + line(formula(first) + "=" + formula(second))
    target = power(data.base, data.exponent) + "=1"
    html = ""
    if target != product(left.items()) + "=" + product(right.items()):
        html += "<p>Разделим положительные степени и объединим множители с общим показателем:</p>"
        html += line(target)
    html += line(sp.latex(data.base) + r">0,\quad " + sp.latex(data.base) + r"\ne1")
    return (
        html
        + "<p>Степень с таким основанием равна единице только при нулевом показателе:</p>"
    )


def proof(a, image=""):
    if a.power_equality.grouping is not None:
        from .exam_trigonometric_power_grouping_proof import proof as grouping

        return grouping(a)
    from .exam_trigonometric_proof import formula

    data = a.power_equality
    html = quotient_domain(a) if data.radicand is not None else ""
    if a.poles and data.radicand is None:
        html += line(a.original)
        html += "<p>До сокращения степеней сохраним область определения исходных тригонометрических отношений:</p>"
        html += "".join(line(formula(p) + r"\ne0") for p in a.poles)
    for text, value in a.identities:
        if value not in (S, C):
            html += line(text + "=" + formula(value))
    if data.radicand is None and data.cleared_power != 1:
        if not a.poles:
            html += line(a.original)
        html += "<p>Умножим уравнение на положительный множитель; множество корней не изменится:</p>"
        html += line(formula(data.cleared_power) + ">0")
    html += power_steps(a)
    if data.absolute_level is not None:
        variable, canceled, level = data.absolute_level
        html += line(formula(data.exponent) + "=0")
        html += "<p>Нули сокращаемого множителя не входят в исходную область определения. Поэтому на ней:</p>"
        html += line(formula(canceled) + r"\ne0")
        html += line(formula(sp.Abs(variable)) + "=" + sp.latex(level))
        html += (
            "<p>Обе части неотрицательны, поэтому возведение в квадрат равносильно:</p>"
        )
        html += line(formula(variable**2) + "=" + sp.latex(level**2))
        html += branch_steps(a)
    elif a.homogeneous is not None and data.radicand is None:
        from .exam_trigonometric_homogeneous_proof import proof as homogeneous

        html += homogeneous(replace(a, identities=()))[1]
    else:
        if a.scale != 1:
            name = "sin" if a.preferred == S else "cos"
            identity = 2 * S * C if a.preferred == S else C * C - S * S
            html += line(formula(data.exponent) + "=0")
            html += "<p>Применим формулу двойного угла:</p>"
            html += line("\\" + name + "2x=" + formula(identity))
        exponent, reduction = reduced_exponent(a)
        html += reduction
        if len(a.branches) > 1:
            html += line(formula(sp.factor(exponent, extension=True)) + "=0")
        if len(a.branches) > 1:
            html += image
        html += branch_steps(a, image if len(a.branches) == 1 else "")
    if data.radicand is not None:
        from .exam_trigonometric_proof import families

        html += (
            "<p>Оставим только серии, удовлетворяющие исходной области определения:</p>"
            if a.series
            else "<p>Все формальные корни исключены исходной областью определения; корней нет.</p>"
        )
        html += "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
    return "<p>Применим формулы приведения и преобразуем исходное уравнение:</p>", html


def branch_steps(a, image=""):
    from ..word_problems.common import UnsupportedCondition
    from .exam_trigonometric_proof import candidate_lines, polynomial

    data = a.power_equality
    if image and any(b.angle_shift for b in a.branches):
        raise UnsupportedCondition(
            "the intermediate inverse-phase figure stage needs review"
        )
    html = ""
    for branch in a.branches:
        options = {
            "allow_inverse": a.allow_inverse,
            "angle": "x" if a.scale == 1 else sp.latex(a.scale) + "x",
            "root_scale": a.scale,
        }
        html += (
            candidate_lines(branch, **options)
            if a.poles
            and data.radicand is None
            and branch.polynomial == branch.variable
            else polynomial(
                branch,
                factorization=True,
                image_after_reduction=image if len(a.branches) == 1 else "",
                **options,
            )
        )
        if data.radicand is not None:
            html += quotient_checks(a, branch)
    return html


def reduced_exponent(a):
    from ..word_problems.common import UnsupportedCondition
    from .exam_trigonometric_proof import formula

    source = a.power_equality.exponent
    if not a.poles or a.power_equality.radicand is not None or a.reduced == source:
        return source, ""
    unit = S * S + C * C - 1
    weight = sp.cancel(sp.rem(source, unit, S) / sp.rem(a.reduced, unit, S))
    if weight.free_symbols or weight.is_real is not True or weight == 0:
        raise UnsupportedCondition(
            "the reduced power equation must preserve the complete unit-circle equation"
        )
    html = "<p>Используем основное тригонометрическое тождество и приведём подобные слагаемые:</p>"
    html += line(formula(S * S + C * C) + "=1")
    if weight != 1:
        html += "<p>Сократим ненулевой числовой множитель:</p>" + line(
            sp.latex(weight) + r"\ne0"
        )
    return a.reduced, html + line(formula(a.reduced) + "=0")


def quotient_domain(a):
    from .exam_trigonometric_proof import formula
    from .exam_trigonometric_radical_product_proof import affine_ratio

    data = a.power_equality
    if data.root_offset:
        return offset_domain(a)
    html = line(a.original)
    html += "<p>Корень в знаменателе должен существовать и быть ненулевым. Запишем исходные ограничения до преобразования степеней:</p>"
    for pole in a.poles:
        html += line(formula(pole) + r"\ne0")
    html += line(data.radicand_text + ">0")
    ratio = affine_ratio(data.radicand)
    if ratio:
        variable, coefficient, constant = ratio
        html += line(
            formula(variable)
            + (">" if coefficient > 0 else "<")
            + sp.latex(sp.simplify(-constant / coefficient))
        )
    elif len(data.radicand.free_symbols) == 1:
        variable = next(iter(data.radicand.free_symbols))
        if sp.cancel(data.radicand / variable).free_symbols == set():
            html += line(
                formula(variable)
                + (">0" if data.radicand.coeff(variable) > 0 else "<0")
            )
    if sp.fraction(data.radicand)[1].free_symbols:
        html += "<p>При исходных ненулевых знаменателях умножим неравенство на положительный квадрат знаменателя:</p>"
        html += line(formula(a.domain) + ">0")
    if data.cleared_power != 1:
        html += "<p>На исходной области определения числитель равен нулю. Умножим его на положительный множитель; множество нулей не изменится:</p>"
        html += line(formula(data.cleared_power) + ">0")
    return html


def offset_domain(a):
    from .exam_trigonometric_proof import formula

    data = a.power_equality
    root = r"\sqrt{" + data.radicand_text + "}"
    denominator = (
        root + ("+" if data.root_offset > 0 else "") + sp.latex(data.root_offset)
    )
    html = line(a.original)
    html += "<p>Запишем область определения: подкоренное выражение неотрицательно, а весь знаменатель ненулевой:</p>"
    html += line(data.radicand_text + r"\ge0") + line(denominator + r"\ne0")
    html += "<p>Сдвинутый корень не требует строгой положительности подкоренного выражения: при нулевом корне весь знаменатель равен ненулевому постоянному слагаемому. Остальные исходные ограничения также сохраняются.</p>"
    if data.root_offset < 0:
        html += "<p>Чтобы исключить нулевой знаменатель, учтём равносильность при неотрицательном подкоренном выражении:</p>"
        html += line(
            root
            + "="
            + sp.latex(-data.root_offset)
            + r"\quad\Longleftrightarrow\quad "
            + data.radicand_text
            + "="
            + sp.latex(data.root_offset**2)
        )
    else:
        html += line(denominator + r"\ge " + sp.latex(data.root_offset) + ">0")
    for pole in a.poles:
        html += line(formula(pole) + r"\ne0")
    if sp.fraction(data.radicand)[1].free_symbols:
        html += "<p>При ненулевом исходном знаменателе умножим неравенство на его положительный квадрат:</p>"
        html += line(formula(a.domain) + r"\ge0")
    if data.cleared_power != 1:
        html += "<p>На исходной области определения числитель равен нулю. Умножим его на положительный множитель; множество нулей не изменится:</p>"
        html += line(formula(data.cleared_power) + ">0")
    return html


def quotient_checks(a, branch):
    from ..word_problems.common import UnsupportedCondition
    from .exam_scalar import compare
    from .exam_trigonometric_inverse import angles
    from .exam_trigonometric_proof import pi

    html = ""
    for value in branch.candidates:
        for q in angles(branch.variable, value, a.allow_inverse):
            if q in branch.residues:
                continue
            substitutions = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
            html += line("x=" + pi(q) + r"+2\pi k")
            if any(sp.simplify(p.subs(substitutions)) == 0 for p in a.poles):
                html += line(r"\text{исходный знаменатель}=0")
            else:
                radicand = sp.simplify(a.power_equality.radicand.subs(substitutions))
                if compare(radicand, sp.S.Zero) >= (1 if a.strict_domain else 0):
                    raise UnsupportedCondition(
                        "a rejected power root must violate its original domain"
                    )
                html += line(
                    r"\text{подкоренное выражение}="
                    + sp.latex(radicand)
                    + (r"\le0" if a.strict_domain else "<0")
                )
            html += "<p>Дробь не определена; эту серию исключаем.</p>"
    return html


def power_steps(a):
    from .exam_trigonometric_proof import formula

    data = a.power_equality
    left, right = dict(data.left_primes), dict(data.right_primes)
    shared = tuple((p, e) for p, e in data.left_primes if e != 0 and e == right.get(p))
    if data.radicand is not None and data.equal_powers is not None and not shared:
        return (
            "<p>Приведём степени к общему положительному основанию:</p>"
            + exponent_steps(a, dict(data.left_primes), dict(data.right_primes))
        )
    html = line(formula(data.left) + "=" + formula(data.right))
    html += (
        "<p>Разложим основания на простые множители и применим свойства степеней:</p>"
    )
    html += line(product(data.left_primes) + "=" + product(data.right_primes))
    if shared:
        html += "<p>Разделим обе части на общий положительный множитель:</p>"
        html += line(product(shared) + ">0")
        for p, _ in shared:
            left.pop(p)
            right.pop(p)
        comparison = product(left.items()) + "=" + product(right.items())
        equal = data.equal_powers
        if not (
            a.poles
            and equal is not None
            and comparison
            == power(equal[0], equal[1]) + "=" + power(equal[0], equal[2])
        ):
            html += line(comparison)
    html += exponent_steps(a, left, right)
    if a.poles and data.equal_powers is not None:
        _, first, second = data.equal_powers
        if not first.is_polynomial(S, C) or not second.is_polynomial(S, C):
            html += "<p>Перенесём показатели в одну часть и сократим одинаковые слагаемые, сохраняя исходные ограничения:</p>"
            html += line(formula(sp.cancel(first - second)) + "=0")
    return html
