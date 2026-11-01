"""Certify the parent's quadratic and cotangent reductions on the unit circle."""

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S


def quadratic(raw):
    for variable, other in ((C, S), (S, C)):
        p = sp.rem(raw, S * S + C * C - 1, other)
        if p.free_symbols == {variable} and sp.degree(p, variable) == 2:
            return variable, p if sp.Poly(p, variable).LC().is_positive else -p
    raise UnsupportedCondition(
        "a quadratic in one original trigonometric function is required"
    )


def cosine_double(raw):
    p = sp.Poly(sp.rem(raw, S * S + C * C - 1, S), C)
    if p.degree() != 4 or any(n % 2 for (n,), _ in p.terms()):
        raise UnsupportedCondition(
            "the parent's double-angle cosine quadratic is required"
        )
    result = sp.expand(sum(v * ((C + 1) / 2) ** (n // 2) for (n,), v in p.terms()))
    return result if sp.Poly(result, C).LC().is_positive else -result


def cotangent(raw, base):
    coefficient = sp.cancel(base / S)
    reduced = sp.cancel(raw / S)
    if (
        coefficient.free_symbols
        or coefficient == 0
        or not reduced.is_polynomial(S, C)
        or sp.Poly(reduced, S, C).total_degree() != 1
        or reduced.subs({S: 0, C: 0}) != 0
        or reduced.coeff(C) == 0
    ):
        raise UnsupportedCondition(
            "the parent's division needs a nonzero original sine base and a homogeneous linear factor"
        )
    return reduced, sp.simplify(-reduced.coeff(S) / reduced.coeff(C))


def cotangent_double(raw):
    constant = raw.subs({S: 0, C: 0})
    homogeneous = sp.expand(raw + constant * (S * S + C * C - 1))
    a, b = homogeneous.coeff(C, 2), homogeneous.coeff(S).coeff(C) / 2
    if (
        sp.expand(homogeneous - a * (C * C - S * S) - 2 * b * S * C) != 0
        or a == 0
        or b == 0
    ):
        raise UnsupportedCondition(
            "a nondegenerate homogeneous double-angle sine/cosine equation is required"
        )
    return a, b, sp.simplify(-b / a)


def certify(raw, base, method):
    if method == "cot":
        cotangent(raw, base)
        return
    check = {
        "quadratic": quadratic,
        "cos_double": cosine_double,
        "cot_double": cotangent_double,
    }.get(method)
    if check is None:
        raise UnsupportedCondition("unknown reviewed variable-log reduction")
    check(raw)


def candidate_notation(raw, base, method, parent_html):
    from .exam_trigonometric_compile import U
    from .exam_trigonometric_inverse import level_series
    from .exam_trigonometric_parameters import affine_families

    if method not in ("cot", "cot_double"):
        return ()
    value = cotangent(raw, base)[1] if method == "cot" else cotangent_double(raw)[2]
    scale = sp.Integer(1 if method == "cot" else 2)
    offset, period = level_series(U, value, True)[0]
    wanted = tuple(
        dict.fromkeys(
            (q, p)
            for q, p, _ in affine_families(parent_html)
            if p == period / scale
            and sp.simplify((q - offset / scale) / p).is_Integer is True
        )
    )
    return wanted if len(wanted) == 1 else ()
