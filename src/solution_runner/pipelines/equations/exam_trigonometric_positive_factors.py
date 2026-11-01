"""Discard a factor only after a strict positivity certificate on the unit circle."""

import sympy as sp
from bs4 import BeautifulSoup

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S


def reviewed(html):
    text = " ".join(
        BeautifulSoup(html, "html.parser")
        .get_text(" ")
        .replace("\xad", "")
        .lower()
        .split()
    )
    return ("сумма" in text and "не обращается в нуль" in text) or (
        "решений не имеет" in text and "одновременно" in text
    )


def positive(poly):
    p = sp.Poly(poly, S, C)
    if p.total_degree() == 1:
        a, b, d = poly.coeff(S), poly.coeff(C), poly.subs({S: 0, C: 0})
        bound = sp.simplify(d - abs(a) - abs(b))
        if compare(bound, sp.S.Zero) > 0:
            return "linear_bound"
        if bound == 0 and a != 0 and b != 0:
            return "linear_corner"
    if all(
        coef.is_positive is True and all(k % 2 == 0 for k in powers)
        for powers, coef in p.terms()
    ):
        pure = [
            any(powers[i] > 0 and powers[1 - i] == 0 for powers, _ in p.terms())
            for i in (0, 1)
        ]
        if p.coeff_monomial(1) > 0:
            return "constant"
        if all(pure):
            return "even"
    return None


def compile_factor(formula):
    from .exam_trigonometric_methods import Equation, constant_angles, parse_equation
    from .exam_trigonometric_poles import compile_atoms

    values, atoms, denominators = parse_equation(formula)
    values, atoms, denominators, _constants = constant_angles(
        values, atoms, denominators
    )
    compiled, poles = compile_atoms(atoms)
    for d in denominators:
        if d.free_symbols:
            pole = sp.fraction(sp.cancel(d.xreplace(compiled)))[0]
            if not pole.is_polynomial(S, C) or sp.Poly(pole, S, C).length() != 1:
                raise UnsupportedCondition(
                    "the original pole must be a sine/cosine monomial"
                )
            poles.update(pole.free_symbols)
    numerator, denominator = sp.fraction(
        sp.cancel((values[0] - values[1]).xreplace(compiled))
    )
    if (
        not numerator.is_polynomial(S, C)
        or sp.Poly(numerator, S, C).total_degree() > 8
        or numerator == 0
    ):
        raise UnsupportedCondition(
            "a nonzero numerator of degree at most eight is required"
        )
    if denominator.free_symbols and (
        not denominator.is_polynomial(S, C)
        or sp.Poly(denominator, S, C).length() != 1
        or not denominator.free_symbols <= poles
    ):
        raise UnsupportedCondition(
            "clearing the denominator requires all its original nonzero factors"
        )
    candidates = [
        numerator,
        sp.expand(sp.rem(numerator, S * S + C * C - 1, S)),
        sp.expand(sp.rem(numerator, S * S + C * C - 1, C)),
    ]
    poly = sp.Poly(numerator, S, C)
    for powers, coefficient in poly.terms():
        difference = poly.total_degree() - sum(powers)
        if coefficient.is_positive is True and difference > 0 and difference % 2 == 0:
            term = coefficient * S ** powers[0] * C ** powers[1]
            candidates.append(
                sp.expand(
                    numerator - term + term * (S * S + C * C) ** (difference // 2)
                )
            )
    for candidate in candidates:
        if sp.rem(candidate - numerator, S * S + C * C - 1, S) != 0:
            raise UnsupportedCondition(
                "the positive-factor rewrite must preserve the unit-circle equation"
            )
        coefficient, factors = sp.factor_list(candidate, S, C, extension=True)
        if len(factors) != 2:
            continue
        for i, (factor, power) in enumerate(factors):
            kind = positive(factor)
            other, other_power = factors[1 - i]
            if (
                kind
                and other.free_symbols in ({S}, {C})
                and sp.degree(other, next(iter(other.free_symbols))) <= 2
            ):
                raw = sp.expand(other**other_power)
                return Equation(
                    raw,
                    tuple(
                        (atoms[s].text.replace(r"\alpha", "x"), value)
                        for s, value in compiled.items()
                        if value not in (S, C)
                    ),
                    sp.S.One,
                    poles=tuple(sorted(poles, key=str)),
                    positive_factorization=(
                        numerator,
                        sp.factor(candidate, extension=True),
                        factor,
                        power,
                        denominator,
                        kind,
                    ),
                )
    raise UnsupportedCondition(
        "one strictly positive factor and one reviewed function factor are required"
    )


def proof(a):
    from .exam_trigonometric_proof import formula, polynomial

    _numerator, factored, factor, _power, denominator, kind = a.positive_factorization
    if kind == "mixed_double":
        return mixed_proof(a)
    html = line(a.original)
    if a.poles:
        html += "<p>Сохраним исходную область определения перед умножением на знаменатель:</p>"
        for pole in a.poles:
            html += line(formula(pole) + r"\ne0")
        html += line(formula(denominator) + r"\ne0")
    for text, value in a.identities:
        html += line(text + "=" + formula(value))
    html += "<p>Используем основное тождество и разложим полученную левую часть на множители:</p>"
    html += (
        line(formula(S * S + C * C) + "=1")
        + line(formula(sp.expand(factored)) + "=0")
        + line(formula(factored) + "=0")
    )
    if kind == "even":
        html += "<p>Все слагаемые выделенного множителя неотрицательны. Для равенства нулю синус и косинус должны были бы одновременно равняться нулю, что противоречит основному тождеству.</p>"
    elif kind == "constant":
        html += "<p>Все слагаемые неотрицательны и есть положительное постоянное слагаемое. Поэтому множитель строго положителен.</p>"
    else:
        html += line(r"-1\le\sin x\le1,\quad -1\le\cos x\le1")
        if kind == "linear_corner":
            html += "<p>Для нулевого значения множителя синус и косинус должны одновременно достичь своих крайних значений:</p>"
            html += line(
                formula(S)
                + "="
                + sp.latex(-sp.sign(factor.coeff(S)))
                + r",\quad "
                + formula(C)
                + "="
                + sp.latex(-sp.sign(factor.coeff(C)))
            )
            html += "<p>Но тогда сумма их квадратов равна 2 вместо 1. Поэтому этот множитель не обращается в нуль.</p>"
        else:
            lower = (
                factor.subs({S: 0, C: 0}) - abs(factor.coeff(S)) - abs(factor.coeff(C))
            )
            html += line(formula(factor) + r"\ge " + sp.latex(lower) + ">0")
    html += line(formula(factor) + ">0")
    html += "<p>Поэтому нули даёт только оставшийся множитель:</p>"
    for b in a.branches:
        html += polynomial(b, allowed_residues=b.residues)
    return "<p>Разложим на множители и проверим знак каждого множителя:</p>", html


def compile_mixed(numerator, denominator, poles, identities):
    from .exam_trigonometric_methods import Equation

    def factors(poly):
        return {
            sp.Poly(f, S, C).monic().as_expr() for f, _ in sp.factor_list(poly, S, C)[1]
        }

    if not denominator.is_polynomial(S, C) or not factors(denominator) <= set().union(
        *(factors(p) for p in poles)
    ):
        raise UnsupportedCondition(
            "every cleared factor must be an original nonzero pole"
        )
    for variable in (S, C):
        reduced = sp.expand(sp.rem(numerator, S * S + C * C - 1, variable))
        coefficient, parts = sp.factor_list(reduced, S, C)
        if len(parts) != 2 or any(power != 1 for _, power in parts):
            continue
        zero = next((f for f, _ in parts if f in (S, C)), None)
        if zero is None:
            continue
        factor = next(f for f, _ in parts if f != zero)
        a, b = factor.coeff(S * C), factor.subs({S: 0, C: 0})
        if (
            a == 0
            or sp.expand(factor - a * S * C - b) != 0
            or compare(abs(2 * b / a), sp.S.One) <= 0
        ):
            continue
        return Equation(
            zero,
            identities,
            sp.S.One,
            poles,
            positive_factorization=(
                numerator,
                coefficient * zero * factor,
                factor,
                1,
                denominator,
                "mixed_double",
            ),
        )
    raise UnsupportedCondition(
        "one zero function factor and a double-angle factor outside [-1,1] are required"
    )


def mixed_proof(a):
    from .exam_trigonometric_compile import T, U
    from .exam_trigonometric_pole_proof import source_sides
    from .exam_trigonometric_proof import families, formula, polynomial
    from .exam_trigonometric_variants import argument

    _, factored, factor, _, _denominator, _ = a.positive_factorization
    angle = argument(a.scale)
    left, right = source_sides(a.original, a.scale)
    multiplier = next((p for p in a.poles if sp.Poly(p, S, C).length() > 1), None)
    if multiplier is None:
        raise UnsupportedCondition("the original ratio multiplier must remain recorded")
    ratio_value = sp.cancel(left * multiplier)
    ratio = T if ratio_value == S / C else U if ratio_value == C / S else None
    if ratio is None:
        raise UnsupportedCondition(
            "the reviewed source must isolate one tangent or cotangent"
        )
    html = line(a.original) + "<p>Сохраним исходные ограничения до умножения:</p>"
    for pole in a.poles:
        html += line(formula(pole, angle) + r"\ne0")
    html += "<p>Умножим обе части на исходный ненулевой знаменатель дроби:</p>"
    rhs = sp.expand(right * multiplier)
    html += line(formula(ratio, angle) + "=" + formula(rhs, angle))
    other = C if ratio == T else S
    reduced_rhs = sp.expand(sp.rem(rhs, S * S + C * C - 1, other))
    html += line(r"\sin^2(" + angle + r")+\cos^2(" + angle + ")=1")
    html += line(formula(ratio_value - reduced_rhs, angle) + "=0")
    html += "<p>Умножим на знаменатель тригонометрического отношения, ненулевой на исходной области определения, и вынесем общий множитель:</p>"
    html += line(formula(sp.expand(factored), angle) + "=0")
    html += line(formula(factored, angle) + "=0")
    doubled = argument(2 * a.scale)
    level = sp.simplify(-2 * factor.subs({S: 0, C: 0}) / factor.coeff(S * C))
    html += "<p>Произведение равно нулю, когда хотя бы один множитель равен нулю. Во второй ветви применим формулу двойного угла:</p>"
    html += line(
        formula(a.raw, angle)
        + "=0"
        + r"\quad\text{или}\quad"
        + formula(factor, angle)
        + "=0"
    )
    html += line(r"\sin(" + doubled + ")=" + sp.latex(level))
    html += "<p>Модуль синуса не превосходит 1, поэтому вторая ветвь корней не имеет. Решим первую и проверим исходные ограничения:</p>"
    for branch in a.branches:
        html += polynomial(
            branch, allowed_residues=None, angle=angle, root_scale=a.scale
        )
        from .exam_trigonometric_pole_proof import checked_levels

        html += checked_levels(a, branch)
    html += "<p>В исходной области определения остаются серии:</p>"
    html += "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
    return "<p>Преобразуем уравнение с сохранением исходной ОДЗ:</p>", html
