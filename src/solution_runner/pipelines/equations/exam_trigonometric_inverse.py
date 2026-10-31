"""Compare principal inverse cosine angles by monotonicity, without approximations."""

from functools import cmp_to_key, lru_cache

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare


def compare_q(a, b):
    difference = sp.expand(sp.simplify(a - b))
    if difference.is_Rational:
        return 1 if difference > 0 else -1 if difference < 0 else 0
    inverse = list(difference.atoms(sp.acos))
    if len(inverse) != 1:
        raise UnsupportedCondition(
            "one principal inverse cosine is required for exact angle comparison"
        )
    angle = inverse[0]
    coefficient = difference.coeff(angle)
    constant = sp.simplify(difference - coefficient * angle)
    multiplier = sp.simplify(coefficient * sp.pi)
    if (
        multiplier.is_Rational is not True
        or multiplier == 0
        or constant.is_Rational is not True
    ):
        raise UnsupportedCondition(
            "a rational pi shift of one inverse angle is required"
        )
    boundary = -constant / multiplier
    order = (
        1
        if boundary < 0
        else -1
        if boundary > 1
        else -compare(angle.args[0], sp.cos(sp.pi * boundary))
    )
    return order * (1 if multiplier > 0 else -1)


def ordered(values):
    return tuple(sorted(set(values), key=cmp_to_key(compare_q)))


@lru_cache(maxsize=128)
def angles(variable, value, allow_inverse=False):
    from .exam_trigonometric import S, table

    try:
        return table(variable, value)
    except UnsupportedCondition:
        if not allow_inverse:
            raise
    if compare(value, -sp.Integer(1)) <= 0 or compare(value, sp.Integer(1)) >= 0:
        raise UnsupportedCondition(
            "a non-tabular principal angle needs a value strictly inside the unit range"
        )
    angle = sp.acos(value) / sp.pi
    if variable == S:
        left = sp.Rational(1, 2) - angle
        if compare(value, sp.Integer(0)) < 0:
            left += 2
        return ordered((left, sp.Rational(1, 2) + angle))
    return ordered((angle, 2 - angle))


def level_series(variable, value, allow_inverse=False):
    from .exam_trigonometric import periodic

    residues = angles(variable, value, allow_inverse)
    if all(q.is_Rational for q in residues):
        return periodic(residues)
    return tuple((q, sp.Integer(2)) for q in residues)


def centred(series):
    result = tuple(
        (q - 2 if period == 2 and compare_q(q, sp.Integer(1)) > 0 else q, period)
        for q, period in series
    )
    return tuple(sorted(result, key=cmp_to_key(lambda a, b: compare_q(a[0], b[0]))))


def select_inverse(series, bounds):
    lo, hi, lc, uc = bounds
    selected = set()
    trace = []
    for offset, period in series:
        if period.is_Rational is not True or period <= 0:
            raise UnsupportedCondition(
                "a positive rational multiple of pi is required as the period"
            )
        start = int(sp.floor((lo - 2) / period)) - 1
        end = int(sp.ceiling((hi + 2) / period)) + 1
        pairs = []
        for k in range(start, end + 1):
            root = offset + k * period
            left, right = compare_q(root, lo), compare_q(root, hi)
            if (left > 0 or (lc and left == 0)) and (right < 0 or (uc and right == 0)):
                pairs.append((k, root))
        values = tuple(root for _, root in pairs)
        selected.update(values)
        trace.append(
            (
                offset,
                period,
                pairs[0][0] if pairs else start,
                pairs[-1][0] if pairs else start - 1,
                values,
            )
        )
    return ordered(selected), tuple(trace)


def decode(value):
    if isinstance(value, str):
        return sp.Rational(value)
    if (
        not isinstance(value, dict)
        or set(value) != {"rational", "acos", "coefficient"}
        or value["coefficient"] not in (-1, 1)
    ):
        raise UnsupportedCondition("unknown audited inverse-angle label")
    argument = sp.Rational(value["acos"])
    if not -1 < argument < 1:
        raise UnsupportedCondition(
            "the audited inverse angle needs a value strictly inside the unit range"
        )
    return (
        sp.Rational(value["rational"])
        + value["coefficient"] * sp.acos(argument) / sp.pi
    )
