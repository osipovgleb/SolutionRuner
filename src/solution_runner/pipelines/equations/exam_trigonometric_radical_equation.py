"""Certify one radical equation before squaring, retaining every original pole."""

from dataclasses import dataclass, replace

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_absolute import R, side
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_methods import ExamAngleParser
from .power_arithmetic import balanced, clean

X = sp.Symbol("x", real=True)
CIRCLE = S * S + C * C - 1


@dataclass(frozen=True)
class RadicalEquation:
    multiplier: sp.Expr
    radicand: sp.Expr
    right: sp.Expr
    squared: sp.Expr
    unreduced_right: sp.Expr
    conditions: tuple
    kind: str
    multiple: int = 0
    cleared: sp.Expr = sp.S.One
    parameters: tuple = ()


def trig_polynomial(function, coefficient, shift=sp.S.Zero):
    if coefficient.is_Integer is not True or abs(coefficient) > 12:
        raise UnsupportedCondition(
            "a bounded integer angle is required after radical reduction"
        )
    value = (sp.sin if function == "sin" else sp.cos)(coefficient * X + shift * sp.pi)
    value = sp.expand(sp.expand_trig(value).xreplace({sp.sin(X): S, sp.cos(X): C}))
    if value.free_symbols - {S, C} or not value.is_polynomial(S, C):
        raise UnsupportedCondition(
            "the radical angle must have an exact unit-circle polynomial"
        )
    return value


def compile_values(values, atoms, denominators, *, extra_symbols=()):
    from .exam_trigonometric_half_products import normalize

    result, atoms, denominators, half_identities = normalize(
        list(values), atoms, denominators
    )
    poles = []
    identities = list(half_identities)
    for symbol, atom in atoms.items():
        k, shift = atom.coefficient, atom.shift
        if atom.function in ("sin", "cos"):
            replacement = trig_polynomial(atom.function, k, shift)
        elif k.q == 2:
            cosine = trig_polynomial("cos", 2 * k, 2 * shift)
            numerator, denominator = (
                (1 - cosine, 1 + cosine)
                if atom.function == "tg"
                else (1 + cosine, 1 - cosine)
            )
            poles.append(denominator)
            square = sp.cancel(numerator / denominator)
            result = [v.xreplace({symbol**2: square}) for v in result]
            denominators = [v.xreplace({symbol**2: square}) for v in denominators]
            if any(v.has(symbol) for v in result):
                raise UnsupportedCondition(
                    "a half-angle ratio is reviewed only through its square"
                )
            identities.append((atom.text.replace(r"\alpha", "x") + "^2", square))
            continue
        else:
            sine = trig_polynomial("sin", k, shift)
            cosine = trig_polynomial("cos", k, shift)
            numerator, denominator = (
                (sine, cosine) if atom.function == "tg" else (cosine, sine)
            )
            poles.append(denominator)
            replacement = sp.cancel(numerator / denominator)
        result = [v.xreplace({symbol: replacement}) for v in result]
        denominators = [v.xreplace({symbol: replacement}) for v in denominators]
        identities.append((atom.text.replace(r"\alpha", "x"), replacement))
    for denominator in denominators:
        numerator, other = sp.fraction(sp.cancel(denominator))
        if numerator.free_symbols:
            poles.append(numerator)
        if other.free_symbols:
            poles.append(other)
    result = [sp.cancel(v) for v in result]
    if any(v.free_symbols - {S, C, R, *extra_symbols} for v in result) or any(
        p.free_symbols - {S, C, *extra_symbols} for p in poles
    ):
        raise UnsupportedCondition("undeclared symbols remain in the radical equation")
    return result, tuple(dict.fromkeys(map(sp.expand, poles))), tuple(identities)


def same(first, second):
    numerator = sp.fraction(sp.cancel(first - second))[0]
    return (
        numerator.is_polynomial(S, C) and sp.simplify(sp.rem(numerator, CIRCLE, S)) == 0
    )


def variable_radicals(text):
    count, start = 0, 0
    while (index := text.find(r"\sqrt{", start)) >= 0:
        inside, start = balanced(text, index + 5)
        count += int("x" in inside)
    return count


def compile_radical(formula, kind):
    from .exam_trigonometric_methods import Equation

    text = clean(formula).removesuffix(".")
    if text.count("=") != 1:
        raise UnsupportedCondition("one radical equality is required")
    atoms, denominators = {}, []
    values = []
    roots = []
    for part in text.split("="):
        if variable_radicals(part):
            value, root = side(part, atoms, denominators)
            values.append(value)
            roots.append(root)
        else:
            values.append(
                ExamAngleParser(part.replace("x", r"\alpha"), atoms, denominators)
                .parse()
                .value
            )
    if len(roots) != 1:
        raise UnsupportedCondition("exactly one complete variable radical is required")
    (left, right, radicand), poles, identities = compile_values(
        [*values, roots[0]], atoms, denominators
    )
    cleared = sp.S.One
    if kind == "safe_square":
        difference, cleared = sp.fraction(sp.cancel(left - right))
        if cleared.free_symbols:
            poles = tuple(dict.fromkeys((*poles, sp.expand(cleared))))
    else:
        difference = sp.expand(left - right)
    multiplier = difference.coeff(R)
    target = -difference.subs(R, 0)
    if multiplier == 0 or sp.expand(difference - multiplier * R + target) != 0:
        raise UnsupportedCondition(
            "the original equation must be affine in its single radical"
        )
    if not multiplier.is_polynomial(S, C) or not target.is_polynomial(S, C):
        raise UnsupportedCondition(
            "the radical multiplier and right side must be polynomials"
        )
    unreduced_right = target
    multiplier = sp.expand(sp.rem(multiplier, CIRCLE, S))
    target = sp.expand(sp.rem(target, CIRCLE, S))
    num, den = sp.fraction(radicand)
    if not all(v.is_polynomial(S, C) for v in (multiplier, target, num, den)):
        raise UnsupportedCondition(
            "the one-radical certificate requires rational unit-circle polynomials"
        )
    if den.free_symbols:
        poles = tuple(dict.fromkeys((*poles, den)))
    if (
        max(sp.Poly(v, S, C).total_degree() for v in (multiplier, target)) > 4
        or max(sp.Poly(v, S, C).total_degree() for v in (num, den)) > 12
    ):
        raise UnsupportedCondition(
            "the radical certificate exceeds its reviewed polynomial degrees"
        )
    squared = sp.expand(multiplier**2 * num - target**2 * den)
    conditions = (sp.expand(num * den), sp.expand(multiplier * target))
    data = RadicalEquation(
        multiplier, radicand, target, squared, unreduced_right, conditions, kind
    )
    raw, multiple = reviewed_numerator(data, poles)
    data = replace(data, multiple=multiple, cleared=cleared)
    return Equation(raw, identities, sp.S.One, poles=poles, radical_equation=data)


def reviewed_numerator(data, poles):
    method = {
        "safe_square": safe_square,
        "half_tangent": half_tangent,
        "amgm": amgm,
        "extremal": extremal,
    }.get(data.kind)
    if method is None:
        raise UnsupportedCondition(
            "an independently reviewed radical method is required"
        )
    return method(data, poles)


def half_tangent(data, poles):
    expected = 4 - 2 / ((1 + C) * (2 * C - 1) ** 2)
    if (
        not same(data.multiplier, S)
        or not same(data.right, 2 + C)
        or not same(data.radicand, expected)
    ):
        raise UnsupportedCondition(
            "the reviewed triple/half-angle method requires its complete rational certificate"
        )
    if set(poles) != {sp.expand((1 + C) * (2 * C - 1) ** 2)}:
        raise UnsupportedCondition(
            "the triple-angle tangent must retain exactly its original pole"
        )
    raw = sp.expand(sp.rem(data.squared, CIRCLE, S))
    _coefficient, factors = sp.factor_list(raw, C, extension=True)
    kept = []
    for factor, power in factors:
        if not any(sp.rem(p, factor, C) == 0 for p in poles):
            kept.append(factor**power)
    raw = sp.expand(sp.prod(kept))
    return raw, 0


def amgm(data, poles):
    if (
        data.multiplier.free_symbols
        or not same(data.radicand, S * C)
        or not same(data.right, data.multiplier * (S + C) / 2)
        or set(poles) != {S, C}
    ):
        raise UnsupportedCondition(
            "both original ratio poles and the positive geometric-mean identity are required"
        )
    return (S - C) ** 2, 0


def extremal(data, poles):
    if poles:
        raise UnsupportedCondition(
            "the reviewed radical extremum has no additional poles"
        )
    if (
        data.multiplier.free_symbols
        or data.multiplier == 0
        or not same(data.right / data.multiplier, -2 * C)
    ):
        raise UnsupportedCondition(
            "the square-root extremum requires its exact cosine right-hand side"
        )
    for multiple in range(1, 12, 2):
        if same(
            data.radicand,
            trig_polynomial("cos", sp.Integer(2))
            - trig_polynomial("sin", sp.Integer(multiple)),
        ):
            sign = sp.sin(multiple * sp.pi / 2)
            return S + sign, multiple
    raise UnsupportedCondition("an independently reviewed radical method is required")


def branches(compiled, preferred, allow_inverse):
    from .exam_trigonometric import solve_branches
    from .exam_trigonometric_domain import restrict, without_poles

    reduced, result = solve_branches(compiled.raw, preferred, allow_inverse)
    result = without_poles(result, compiled.poles)
    for condition in compiled.radical_equation.conditions:
        result = restrict(result, condition)
    return reduced, result


def safe_square(data, poles):
    if data.multiplier.free_symbols or data.multiplier == 0:
        raise UnsupportedCondition(
            "safe squaring requires a nonzero constant root coefficient"
        )
    right = sp.cancel(data.right / data.multiplier)
    if (
        not right.is_polynomial(S, C)
        or sp.Poly(right, S, C).total_degree() > 1
        or not data.radicand.is_polynomial(S, C)
        or sp.Poly(data.radicand, S, C).total_degree() > 2
    ):
        raise UnsupportedCondition(
            "an affine right side and quadratic unit-circle radicand are required"
        )
    for pole in poles:
        _, factors = sp.factor_list(pole, S, C)
        if not factors or any(f not in (S, C) for f, _ in factors):
            raise UnsupportedCondition(
                "safe squaring retains only reviewed sine/cosine poles"
            )
    for variable, other in ((S, C), (C, S)):
        reduced = sp.expand(sp.rem(data.squared, CIRCLE, other))
        if not reduced.has(other) and sp.degree(reduced, variable) in (1, 2):
            return reduced, 0
    raise UnsupportedCondition(
        "the squared equation must reduce to one quadratic trigonometric variable"
    )
