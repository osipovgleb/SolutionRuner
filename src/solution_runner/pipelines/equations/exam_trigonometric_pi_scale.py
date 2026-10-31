"""Normalize rational multiples of pi in angles and select rational real roots."""

from dataclasses import replace

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare, enclose


def normalize(atoms, denominators):
    if not any(a.coefficient.has(sp.pi) for a in atoms.values()):
        return atoms, sp.S.One
    if any(d.free_symbols for d in denominators) or any(
        sp.cancel(a.coefficient / sp.pi).is_Rational is not True for a in atoms.values()
    ):
        raise UnsupportedCondition(
            "pi-scaled angles require a common unit and no variable denominators"
        )
    return {
        symbol: replace(atom, coefficient=sp.cancel(atom.coefficient / sp.pi))
        for symbol, atom in atoms.items()
    }, sp.pi


def finish(a):
    from .exam_trigonometric_inverse import centred

    if a.selection_method != "inequalities" or a.affine or a.translation or a.poles:
        raise UnsupportedCondition(
            "pi-scaled angles require direct selection by inequalities"
        )
    bounds = tuple(sp.simplify(q * sp.pi) for q in a.bounds[:2])
    for bound in bounds:
        if (
            bound.is_algebraic is not True
            or bound.free_symbols
            or sp.count_ops(bound) > 12
        ):
            raise UnsupportedCondition("bounded algebraic real endpoints are required")
        lo, hi = enclose(bound)
        if lo < -1000 or hi > 1000:
            raise UnsupportedCondition(
                "the algebraic endpoint exceeds the reviewed range"
            )
    multiple = sp.cancel(a.scale / sp.pi)
    if multiple <= 0 or multiple > 100:
        raise UnsupportedCondition(
            "a positive bounded rational pi angle multiplier is required"
        )
    series = tuple((q / multiple, p / multiple) for q, p in centred(a.series))
    if any(
        q.is_Rational is not True or p.is_Rational is not True or p <= 0
        for q, p in series
    ):
        raise UnsupportedCondition(
            "pi-scaled angles must yield rational real progressions"
        )
    lower, upper = bounds
    lc, uc = a.bounds[2:]
    selected, traces = set(), []
    for offset, period in series:
        start = int(sp.ceiling((lower - offset) / period))
        end = int(sp.floor((upper - offset) / period))
        if not lc and compare(offset + start * period, lower) == 0:
            start += 1
        if not uc and compare(offset + end * period, upper) == 0:
            end -= 1
        certify_limits(offset, period, start, end, bounds, (lc, uc))
        if end - start > 200:
            raise UnsupportedCondition("too many progression members in the interval")
        values = tuple(offset + k * period for k in range(start, end + 1))
        selected.update(values)
        traces.append(
            (
                offset / sp.pi,
                period / sp.pi,
                start,
                end,
                tuple(v / sp.pi for v in values),
            )
        )
    return replace(
        a,
        series=tuple((q / sp.pi, p / sp.pi) for q, p in series),
        selected=tuple(v / sp.pi for v in sorted(selected)),
        selections=tuple(traces),
    )


def certify_limits(offset, period, start, end, bounds, closed):
    lower, upper = bounds
    lc, uc = closed
    first, last = offset + start * period, offset + end * period
    left, before = compare(first, lower), compare(first - period, lower)
    right, after = compare(last, upper), compare(last + period, upper)
    if not (
        (left >= 0 if lc else left > 0)
        and (before < 0 if lc else before <= 0)
        and (right <= 0 if uc else right < 0)
        and (after > 0 if uc else after >= 0)
    ):
        raise UnsupportedCondition(
            "integer progression limits failed exact endpoint checks"
        )
