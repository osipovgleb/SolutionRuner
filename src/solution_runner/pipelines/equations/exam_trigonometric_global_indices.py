"""Convert physical polynomial domains into certified windows of integer indices."""

import itertools
from dataclasses import dataclass
from functools import cmp_to_key

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare, enclose

X = sp.Symbol("x", real=True)


@dataclass(frozen=True)
class IndexedFamily:
    offset: sp.Rational
    period: sp.Rational
    parameter: str
    windows: tuple
    intervals: tuple
    coefficient: sp.Expr

    def accepts(self, index):
        return any(
            (lo is None or index >= lo) and (hi is None or index <= hi)
            for lo, hi in self.windows
        )


def real_roots(polynomial):
    found = sp.roots(polynomial, X)
    if sum(found.values()) != sp.degree(polynomial, X) or any(
        r.is_real is not True for r in found
    ):
        raise UnsupportedCondition(
            "the global polynomial needs a complete real root certificate"
        )
    reconstructed = sp.Poly(polynomial, X).LC() * sp.prod(
        (X - r) ** n for r, n in found.items()
    )
    if sp.simplify(sp.expand(reconstructed - polynomial)) != 0:
        raise UnsupportedCondition("the global polynomial factorization is incomplete")
    result = tuple(sorted(found, key=cmp_to_key(compare)))
    for root in result:
        enclose(root)
    return result


def positive_intervals(polynomial):
    cuts = (-sp.oo, *real_roots(polynomial), sp.oo)
    result = []
    for lo, hi in itertools.pairwise(cuts):
        sample = hi - 1 if lo == -sp.oo else lo + 1 if hi == sp.oo else (lo + hi) / 2
        if compare(sp.simplify(polynomial.subs(X, sample)), sp.S.Zero) > 0:
            result.append((lo, hi))
    return tuple(result)


def exact_floor(value):
    value = sp.simplify(value)
    lower, _ = enclose(value)
    candidate = lower.numerator // lower.denominator
    for _ in range(4):
        if compare(value, sp.Integer(candidate)) < 0:
            candidate -= 1
        elif compare(value, sp.Integer(candidate + 1)) >= 0:
            candidate += 1
        else:
            return candidate
    raise UnsupportedCondition("an exact integer bound could not be certified")


def windows(intervals, offset, period):
    result = []
    for lo, hi in intervals:
        start = (
            None if lo == -sp.oo else exact_floor((lo / sp.pi - offset) / period) + 1
        )
        end = None if hi == sp.oo else -exact_floor(-(hi / sp.pi - offset) / period) - 1
        if start is not None and end is not None and start > end:
            continue
        if result and (
            result[-1][1] is None or start is None or start <= result[-1][1] + 1
        ):
            previous = result.pop()
            result.append(
                (
                    previous[0],
                    None
                    if previous[1] is None or end is None
                    else max(previous[1], end),
                )
            )
        else:
            result.append((start, end))
    return tuple(result)


def selected(family, bounds):
    from .exam_trigonometric import select

    values, _ = select(((family.offset, family.period),), bounds)
    return tuple(
        q
        for q in values
        if family.accepts(int(sp.cancel((q - family.offset) / family.period)))
    )


def displayed(family):
    if family.windows == ((None, 0),):
        return family.offset, -family.period
    return family.offset, family.period


def integer_set(family, *, reindexed=False):
    ranges = family.windows
    if not ranges:
        return r"\varnothing"
    if ranges == ((None, None),):
        return r"\mathbb Z"
    if ranges == ((None, 0),):
        return r"\mathbb N\cup\{0\}" if reindexed else r"\mathbb Z_{\le0}"
    if ranges == ((0, None),):
        return r"\mathbb N\cup\{0\}"
    if len(ranges) == 1 and ranges[0][0] is None:
        return r"\mathbb Z_{\le " + str(ranges[0][1]) + "}"
    if len(ranges) == 1 and ranges[0][1] is None:
        return r"\mathbb Z_{\ge " + str(ranges[0][0]) + "}"
    if len(ranges) == 1 and ranges[0][0] is not None and ranges[0][1] is not None:
        lo, hi = ranges[0]
        values = (
            ";".join(map(str, range(lo, hi + 1)))
            if hi - lo <= 4
            else f"{lo};{lo + 1};" + r"\ldots;" + f"{hi - 1};{hi}"
        )
        return r"\{" + values + r"\}"
    if ranges and ranges[0][0] is None and ranges[-1][1] is None:
        excluded = []
        for (_, hi), (lo, _) in itertools.pairwise(ranges):
            if lo - hi > 32:
                raise UnsupportedCondition(
                    "the finite index gap exceeds the reviewed display size"
                )
            excluded.extend(range(hi + 1, lo))
        return r"\mathbb Z" + (
            r"\setminus\{" + ";".join(map(str, excluded)) + r"\}" if excluded else ""
        )
    clauses = []
    for lo, hi in ranges:
        k = family.parameter
        clauses.append(
            (str(lo) + r"\le " if lo is not None else "")
            + k
            + (r"\le " + str(hi) if hi is not None else "")
        )
    return (
        r"\{"
        + family.parameter
        + r"\in\mathbb Z\mid "
        + r"\text{ или }".join(clauses)
        + r"\}"
    )
