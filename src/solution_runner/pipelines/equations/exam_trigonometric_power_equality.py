"""Certify one common exponent of complete positive power products."""

import re
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_methods import Equation
from .exam_trigonometric_power_parser import PositivePowerParser
from .exam_trigonometric_radical_equation import compile_values
from .power_arithmetic import balanced, clean


@dataclass(frozen=True)
class PowerEquality:
    left: sp.Expr
    right: sp.Expr
    left_primes: tuple
    right_primes: tuple
    base: sp.Expr
    exponent: sp.Expr
    equal_powers: tuple | None = None


def reviewed(formula):
    text = clean(formula)
    for m in re.finditer(r"(?:\d|\))\^\{", text):
        exponent, _ = balanced(text, m.end() - 1)
        if any(f in exponent for f in (r"\sin", r"\cos", r"\tg", r"\ctg")):
            return True
    return False


def review_parent(html):
    soup = BeautifulSoup(html, "html.parser")
    forms = [clean(n["data-inline-latex"]) for n in soup.select("[data-inline-latex]")]
    text = soup.get_text(" ").replace("\xad", "").lower()
    if (
        not any(reviewed(f) for f in forms)
        or any(re.search(r"(?<![A-Za-z])[tyuzv]=", f) for f in forms)
        or any(s in text for s in ("случа", "другое решение", "ещё одно решение"))
        or r"\log" in " ".join(forms)
    ):
        raise UnsupportedCondition(
            "the parent must use direct equality of positive powers without another method"
        )


def prime_logs(value):
    if value == 1:
        return {}
    if value.is_Rational:
        if not 0 < value <= 10**8 or value.q > 10**8:
            raise UnsupportedCondition(
                "bounded positive rational power factors are required"
            )
        result = {p: sp.Integer(n) for p, n in sp.factorint(value.p).items()}
        for p, n in sp.factorint(value.q).items():
            result[p] = result.get(p, 0) - n
        return result
    if value.is_Mul:
        result = {}
        for factor in value.args:
            for p, exponent in prime_logs(factor).items():
                result[p] = result.get(p, 0) + exponent
        return result
    if value.is_Pow:
        return {
            p: exponent * value.exp for p, exponent in prime_logs(value.base).items()
        }
    raise UnsupportedCondition(
        "each complete side must be a positive rational power product"
    )


def common_exponent(left, right):
    vectors = {
        p: sp.expand(left.get(p, 0) - right.get(p, 0))
        for p in sorted(left.keys() | right.keys())
    }
    vectors = {p: e for p, e in vectors.items() if e != 0}
    if not vectors:
        raise UnsupportedCondition(
            "an exponential identity requires its complete original domain"
        )
    first = next(iter(vectors.values()))
    ratios = {p: sp.cancel(e / first) for p, e in vectors.items()}
    if any(
        e.is_Rational is not True or abs(e) > 100 or e.q > 100 for e in ratios.values()
    ):
        raise UnsupportedCondition(
            "independent prime exponent directions cannot be equated separately"
        )
    denominator = sp.ilcm(1, *(e.q for e in ratios.values()))
    integers = {p: e * denominator for p, e in ratios.items()}
    divisor = sp.igcd(0, *integers.values())
    base = sp.prod(sp.Integer(p) ** (e / divisor) for p, e in integers.items())
    exponent = sp.expand(first * divisor / denominator)
    if (
        not exponent.is_polynomial(S, C)
        or not 1 <= sp.Poly(exponent, S, C).total_degree() <= 3
    ):
        raise UnsupportedCondition(
            "a bounded polynomial exponent with no original trig poles is required"
        )
    coefficients = sp.Poly(exponent, S, C).coeffs()
    if any(e.is_real is not True or abs(e) > 1000 for e in coefficients):
        raise UnsupportedCondition(
            "bounded real algebraic exponent coefficients are required"
        )
    if exponent.free_symbols == {C} and sp.Poly(exponent, C).LC() < 0:
        base, exponent = 1 / base, -exponent
    return base, exponent


def scaled_exponent(exponent, preferred, scale):
    if scale == 1:
        return exponent
    from .exam_trigonometric_radical_equation import same

    if scale != 2 or preferred not in (S, C):
        raise UnsupportedCondition(
            "only the parent's reviewed double-angle power method is supported"
        )
    identity = 2 * S * C if preferred == S else C * C - S * S
    reduced = sp.expand(sp.rem(exponent, S * S + C * C - 1, S))
    coefficient = (
        reduced.coeff(S * C) / 2 if preferred == S else reduced.coeff(C, 2) / 2
    )
    reduced_identity = 2 * S * C if preferred == S else 2 * C * C - 1
    constant = sp.expand(reduced - coefficient * reduced_identity).subs({S: 0, C: 0})
    if coefficient == 0 or not same(exponent, coefficient * identity + constant):
        raise UnsupportedCondition(
            "the complete exponent must be affine in the original double angle"
        )
    return coefficient * preferred + constant


def compile_equality(formula, parent_html, *, preferred=None, scale=sp.S.One):
    review_parent(parent_html)
    text = clean(formula).removesuffix(".")
    if text.count("=") != 1:
        raise UnsupportedCondition("one complete positive-power equality is required")
    atoms, denominators = {}, []
    nodes = [
        PositivePowerParser(side.replace("x", r"\alpha"), atoms, denominators).parse()
        for side in text.split("=")
    ]
    if not atoms or any(a.variable != r"\alpha" for a in atoms.values()):
        raise UnsupportedCondition("all original exponents must use the same angle x")
    values, poles, identities = compile_values(
        [n.value for n in nodes], atoms, denominators
    )
    left, right = (prime_logs(value) for value in values)
    for pole in poles:
        prime_logs(pole)
    base, exponent = common_exponent(left, right)
    from .exam_trigonometric_power_style import equal_base, equal_sides, scaled_angle

    preferred, scale = scaled_angle(parent_html) or (preferred, scale)
    data = PowerEquality(
        *values,
        tuple(sorted(left.items())),
        tuple(sorted(right.items())),
        base,
        exponent,
        equal_sides(left, right, base, equal_base(parent_html)),
    )
    return Equation(
        scaled_exponent(exponent, preferred, scale),
        identities,
        scale,
        power_equality=data,
    )
