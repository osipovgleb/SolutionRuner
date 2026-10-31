"""Compare principal inverse angles by monotonicity, without approximations."""

from functools import cmp_to_key, lru_cache

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare


def compare_q(a, b):
    difference = sp.expand(sp.simplify(a - b))
    if difference.is_Rational:
        return 1 if difference > 0 else -1 if difference < 0 else 0
    tangents = list(difference.atoms(sp.atan))
    if tangents:
        return compare_tangents(difference, tangents)
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


def compare_tangents(difference, angles):
    coefficients = [sp.simplify(difference.coeff(a) * sp.pi) for a in angles]
    constant = sp.simplify(
        difference - sum(c * a / sp.pi for c, a in zip(coefficients, angles))
    )
    if constant.is_Rational is not True or any(
        c.is_Rational is not True or c == 0 for c in coefficients
    ):
        raise UnsupportedCondition(
            "rational shifts of principal arctangents are required"
        )
    if len(angles) == 1:
        boundary = -constant / coefficients[0]
        order = (
            1
            if boundary <= -sp.Rational(1, 2)
            else -1
            if boundary >= sp.Rational(1, 2)
            else compare(angles[0].args[0], sp.tan(sp.pi * boundary))
        )
        return order * (1 if coefficients[0] > 0 else -1)
    if len(angles) == 2 and coefficients[0] == -coefficients[1]:
        if constant == 0:
            return compare(angles[0].args[0], angles[1].args[0]) * (
                1 if coefficients[0] > 0 else -1
            )
        if abs(constant) >= abs(coefficients[0]):
            return 1 if constant > 0 else -1
    if constant == 0:
        signs = [
            compare(a.args[0], sp.Integer(0)) * (1 if c > 0 else -1)
            for a, c in zip(angles, coefficients)
        ]
        if all(s >= 0 for s in signs):
            return 1 if any(signs) else 0
        if all(s <= 0 for s in signs):
            return -1
    raise UnsupportedCondition(
        "the arctangent difference is outside the reviewed exact comparison"
    )


def ordered(values):
    return tuple(sorted(set(values), key=cmp_to_key(compare_q)))


@lru_cache(maxsize=128)
def angles(variable, value, allow_inverse=False):
    from .exam_trigonometric import S, T, U, table

    if variable == U:
        offset = cotangent_angle(value)
        return ordered((offset, offset + 1))
    if variable == T:
        q = sp.atan(value) / sp.pi
        offset = q + 1 if compare(value, sp.Integer(0)) < 0 else q
        return ordered((offset, offset + 1))

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
    if compare(value, sp.Integer(0)) < 0:
        angle = 1 - sp.acos(-value) / sp.pi
    return ordered((angle, 2 - angle))


def level_series(variable, value, allow_inverse=False):
    from .exam_trigonometric import T, U, periodic

    if variable == U:
        return ((cotangent_angle(value), sp.Integer(1)),)
    if variable == T:
        return ((sp.atan(value) / sp.pi, sp.Integer(1)),)

    residues = angles(variable, value, allow_inverse)
    if all(q.is_Rational for q in residues):
        return periodic(residues)
    return tuple((q, sp.Integer(2)) for q in residues)


def cotangent_angle(value):
    if value == 0:
        return sp.Rational(1, 2)
    q = sp.atan(1 / value) / sp.pi
    return q + 1 if compare(value, sp.Integer(0)) < 0 else q


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
        or set(value)
        not in (
            {"rational", "acos", "coefficient"},
            {"rational", "atan", "coefficient"},
        )
        or value["coefficient"] not in (-1, 1)
    ):
        raise UnsupportedCondition("unknown audited inverse-angle label")
    function = sp.atan if "atan" in value else sp.acos
    argument = sp.Rational(value["atan"] if "atan" in value else value["acos"])
    if function == sp.acos and not -1 < argument < 1:
        raise UnsupportedCondition(
            "the audited inverse angle needs a value strictly inside the unit range"
        )
    return (
        sp.Rational(value["rational"])
        + value["coefficient"] * function(argument) / sp.pi
    )
