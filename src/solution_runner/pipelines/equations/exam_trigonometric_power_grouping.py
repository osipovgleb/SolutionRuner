"""Factor two independent positive-power directions before equating exponents."""

from dataclasses import dataclass

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_power_equality import prime_logs

X, Y = sp.symbols("X Y", positive=True)


@dataclass(frozen=True)
class PowerGrouping:
    argument: sp.Expr
    argument_text: str
    bases: tuple
    polynomial: sp.Expr
    positive_factor: sp.Expr
    univariate: sp.Expr
    mixed: sp.Expr
    variable: sp.Symbol
    power: int
    level: sp.Rational
    ratio: sp.Rational
    substitution: str | None = None
    order: tuple = ()
    figure_after_grouping: bool = False
    reverse_mixed: bool = False


def affine(exponent, argument):
    if not exponent.is_polynomial(S, C):
        raise UnsupportedCondition("bounded polynomial power exponents are required")
    monomial, coefficient = next(
        (m, c) for m, c in sp.Poly(argument, S, C).terms() if m != (0, 0)
    )
    slope = sp.Poly(exponent, S, C).coeff_monomial(monomial) / coefficient
    offset = sp.expand(exponent - slope * argument)
    if any(
        v.is_Rational is not True or abs(v) > 100 or v.q > 12 for v in (slope, offset)
    ):
        raise UnsupportedCondition("each whole power needs one bounded affine argument")
    return slope, offset


def terms(expression, argument):
    result = []
    for term in sp.Add.make_args(sp.expand(expression)):
        sign = -1 if term.could_extract_minus_sign() else 1
        constant, slopes = sp.Integer(sign), {}
        for prime, exponent in prime_logs(sign * term).items():
            slope, offset = affine(exponent, argument)
            slopes[prime] = slope
            constant *= sp.Integer(prime) ** offset
        if constant.is_Rational is not True or abs(constant) > 10**8:
            raise UnsupportedCondition(
                "bounded rational whole-term coefficients required"
            )
        result.append((constant, slopes))
    return result


def bases_for(records):
    directions = {}
    for prime in sorted(set().union(*(slopes.keys() for _, slopes in records))):
        vector = tuple(slopes.get(prime, sp.S.Zero) for _, slopes in records)
        if not any(vector):
            continue
        denominator = sp.ilcm(1, *(v.q for v in vector))
        divisor = sp.igcd(0, *(v * denominator for v in vector))
        weight = sp.Rational(divisor, denominator)
        if next(v for v in vector if v) < 0:
            weight = -weight
        primitive = tuple(v / weight for v in vector)
        directions[primitive] = (
            directions.get(primitive, 1) * sp.Integer(prime) ** weight
        )
    if len(directions) != 2:
        return None
    bases = tuple(sorted(directions.values(), key=sp.default_sort_key))
    if any(
        b.is_Rational is not True or not sp.Rational(1, 10000) <= b <= 10000 or b == 1
        for b in bases
    ):
        raise UnsupportedCondition("two bounded positive rational bases are required")
    return bases


def polynomial_for(records, bases):
    prime_bases = tuple(prime_logs(b) for b in bases)
    polynomial = sp.S.Zero
    for constant, slopes in records:
        powers = []
        for base in prime_bases:
            prime, coefficient = next(iter(base.items()))
            power = slopes.get(prime, sp.S.Zero) / coefficient
            if power.is_Integer is not True or abs(power) > 12:
                raise UnsupportedCondition(
                    "bounded integer power directions are required"
                )
            powers.append(power)
        for prime in slopes.keys() | set().union(*(b.keys() for b in prime_bases)):
            if slopes.get(prime, 0) != sum(
                p * b.get(prime, 0) for p, b in zip(powers, prime_bases)
            ):
                raise UnsupportedCondition(
                    "every original prime exponent must be retained"
                )
        polynomial += constant * X ** powers[0] * Y ** powers[1]
    if polynomial == 0:
        raise UnsupportedCondition("a power identity needs a separate domain proof")
    minimum = [
        min(t.as_powers_dict().get(v, 0) for t in sp.Add.make_args(polynomial))
        for v in (X, Y)
    ]
    factor = X ** minimum[0] * Y ** minimum[1]
    reduced = sp.Poly(sp.expand(polynomial / factor), X, Y, domain=sp.QQ)
    if reduced.total_degree() > 12:
        raise UnsupportedCondition("a bounded two-base polynomial is required")
    return reduced.monic().as_expr(), factor, reduced.LC()


def factor(polynomial, bases):
    univariate, mixed = {}, sp.S.One
    for value, multiplicity in sp.factor_list(polynomial, X, Y)[1]:
        variables = value.free_symbols
        if len(variables) == 1:
            variable = next(iter(variables))
            univariate[variable] = univariate.get(variable, 1) * value**multiplicity
        else:
            mixed *= value**multiplicity
    if len(univariate) != 1:
        raise UnsupportedCondition(
            "one unit-range branch and one equality branch required"
        )
    variable, value = next(iter(univariate.items()))
    polynomial = sp.Poly(value, variable).monic()
    power, level = polynomial.degree(), -polynomial.TC()
    if polynomial.as_expr() != variable**power - level or level <= 0:
        raise UnsupportedCondition(
            "the excluded power branch must be a complete binomial"
        )
    base = bases[(X, Y).index(variable)] ** power
    if level <= max(base, 1 / base):
        raise UnsupportedCondition(
            "the extra power branch must lie outside the unit range"
        )
    items = sp.Poly(mixed, X, Y).terms()
    if len(items) != 2 or items[0][1] != -items[1][1]:
        raise UnsupportedCondition("the remaining branch must equate two whole powers")
    (m, _), (n, _) = items
    ratio = sp.prod(b ** (i - j) for b, i, j in zip(bases, m, n))
    if ratio == 1:
        raise UnsupportedCondition("an identity factor cannot be discarded")
    return (
        variable,
        power,
        level,
        ratio,
        polynomial.as_expr(),
        sp.Poly(mixed, X, Y).monic().as_expr(),
    )


def compile_grouping(formula, parent_html):
    from .exam_trigonometric_methods import Equation
    from .exam_trigonometric_power_equality import PowerEquality, reviewed
    from .exam_trigonometric_power_grouping_style import candidate, review
    from .exam_trigonometric_power_polynomial import source
    from .exam_trigonometric_radical_equation import trig_polynomial

    if not reviewed(formula) or not candidate(parent_html):
        return None
    expression, poles, identities, domain, wrapper, _ = source(formula)
    if poles or domain is not None or wrapper is not None:
        return None
    arguments = tuple(dict.fromkeys(v for _, v in identities))
    if len(arguments) != 1 or len(sp.Add.make_args(expression)) != 4:
        return None
    argument = arguments[0]
    shape = next(
        (
            (v, n)
            for v in (S, C)
            for n in range(1, 4)
            if argument == trig_polynomial("sin" if v == S else "cos", sp.Integer(n))
        ),
        None,
    )
    if shape is None:
        return None
    records = terms(expression, argument)
    bases = bases_for(records)
    if bases is None:
        return None
    polynomial, positive, _ = polynomial_for(records, bases)
    variable, power, level, ratio, univariate, mixed = factor(polynomial, bases)
    data = PowerGrouping(
        argument,
        identities[0][0],
        bases,
        polynomial,
        positive,
        univariate,
        mixed,
        variable,
        power,
        level,
        ratio,
    )
    data = review(data, parent_html)
    left = sp.Pow(data.ratio, argument, evaluate=False)
    equality = PowerEquality(
        left,
        sp.S.One,
        tuple(sorted(prime_logs(left).items())),
        (),
        data.ratio,
        argument,
        grouping=data,
    )
    return Equation(shape[0], (), sp.Integer(shape[1]), power_equality=equality)
