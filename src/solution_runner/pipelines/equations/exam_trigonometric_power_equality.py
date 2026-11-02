"""Certify one common exponent of complete positive power products."""

import re
from dataclasses import dataclass, replace

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
    radicand: sp.Expr | None = None
    radicand_text: str | None = None
    cleared_power: sp.Expr = sp.S.One


def reviewed(formula):
    text = clean(formula)
    for m in re.finditer(r"(?:\d|\))\^\{", text):
        exponent, _ = balanced(text, m.end() - 1)
        if any(f in exponent for f in (r"\sin", r"\cos", r"\tg", r"\ctg")):
            return True
    return False


def parent_forms(html):
    soup = BeautifulSoup(html, "html.parser")
    forms = [clean(n["data-inline-latex"]) for n in soup.select("[data-inline-latex]")]
    text = soup.get_text(" ").replace("\xad", "").lower()
    if (
        any(re.search(r"(?<![A-Za-z])[tyuzv]=", f) for f in forms)
        or any(
            s in text
            for s in ("случа", "другое решение", "ещё одно решение", "еще одно решение")
        )
        or r"\log" in " ".join(forms)
    ):
        raise UnsupportedCondition(
            "the parent must use direct equality of positive powers without another method"
        )
    return forms


def review_parent(html):
    if not any(reviewed(f) for f in parent_forms(html)):
        raise UnsupportedCondition(
            "the parent must use direct equality of positive powers without another method"
        )


def review_quotient_parent(html, exponent):
    from .exam_trigonometric_compile import compile_equation

    forms = parent_forms(html)
    if any(reviewed(f) for f in forms):
        return
    for value in forms:
        parts = re.split(
            r"\\(?:iff|Leftrightarrow|quad)|\\(?:begin|end)\{(?:cases|aligned)\}|\\\\",
            value.replace("&", ""),
        )
        for part in parts:
            part = part.removeprefix(r"\left[").removesuffix(r"\right.").strip(".,;")
            if part.count("=") != 1 or any(
                token in part for token in ("<", ">", r"\gt", r"\lt", r"\ge", r"\le")
            ):
                continue
            try:
                raw, _ = compile_equation(part)
            except UnsupportedCondition:
                continue
            weight = sp.cancel(raw / exponent)
            if not weight.free_symbols and weight.is_real is True and weight != 0:
                return
    raise UnsupportedCondition(
        "the parent must retain the complete computed power-exponent equation"
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
    for pole in poles:
        prime_logs(pole)
    return equation(values, identities, parent_html, preferred, scale)


def equation(
    values,
    identities,
    parent_html,
    preferred,
    scale,
    *,
    radicand=None,
    radicand_text=None,
    poles=(),
    cleared_power=sp.S.One,
):
    left, right = (prime_logs(value) for value in values)
    base, exponent = common_exponent(left, right)
    from .exam_trigonometric_power_style import equal_base, equal_sides, scaled_angle

    preferred, scale = scaled_angle(parent_html) or (preferred, scale)
    if radicand is not None:
        review_quotient_parent(parent_html, exponent)
        if scale != 1:
            raise UnsupportedCondition(
                "a radical power quotient needs its original angle"
            )
    presented_base = equal_base(parent_html)
    if radicand is not None and presented_base is None:
        presented_base = base
    data = PowerEquality(
        *values,
        tuple(sorted(left.items())),
        tuple(sorted(right.items())),
        base,
        exponent,
        equal_sides(left, right, base, presented_base),
        radicand,
        radicand_text,
        cleared_power,
    )
    numerator, denominator = sp.fraction(radicand) if radicand is not None else (0, 1)
    return Equation(
        scaled_exponent(exponent, preferred, scale),
        identities,
        scale,
        poles=poles,
        domain=sp.expand(numerator * denominator) if radicand is not None else None,
        strict_domain=radicand is not None,
        power_equality=data,
    )


def compile_quotient(formula, parent_html, *, preferred=None, scale=sp.S.One):
    from .exam_trigonometric_power_polynomial import source
    from .exam_trigonometric_strict_quotient import operands

    parts = operands(formula)
    if parts is None or not reviewed(formula):
        return None
    expression, poles, identities, radicand, _wrapper, strict = source(
        formula, rational_domain=True
    )
    numerator, divisor = sp.fraction(expression)
    prime_logs(divisor)
    terms = sp.Add.make_args(numerator)
    positive = [t for t in terms if not t.could_extract_minus_sign()]
    negative = [-t for t in terms if t.could_extract_minus_sign()]
    if not strict or len(positive) != 1 or len(negative) != 1:
        raise UnsupportedCondition("two complete positive power products are required")
    if any(p not in (S, C) for p in poles):
        raise UnsupportedCondition(
            "only original sine/cosine power-quotient poles are reviewed"
        )
    return equation(
        [positive[0], negative[0]],
        identities,
        parent_html,
        preferred,
        scale,
        radicand=radicand,
        radicand_text=parts[1],
        poles=poles,
        cleared_power=divisor,
    )


def prepare(a, parent_html):
    if a.power_equality is None or a.power_equality.radicand is None or not a.series:
        return a
    from .exam_trigonometric import select
    from .exam_trigonometric_inverse import centred
    from .exam_trigonometric_parameters import affine_families
    from .exam_trigonometric_selection import equivalent_series

    declared = {
        (q % p, p): (q, p)
        for q, p, _ in affine_families(parent_html)
        if equivalent_series((*a.series, (q, p)), a.series)
    }
    source = tuple(declared.values())
    series = (
        source if source and equivalent_series(source, a.series) else centred(a.series)
    )
    selected, trace = select(series, a.bounds)
    return replace(
        a,
        series=series,
        selected=selected,
        selections=trace,
        series_aligned=series != a.series,
    )
