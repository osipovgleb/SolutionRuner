"""Select progression members using the interval length and the series step."""

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from ..word_problems.water_season_proof import inline


def progressions(a):
    from .exam_trigonometric_proof import pi, series_lines

    lo, hi, _, _ = a.bounds
    length = hi - lo
    html = (
        "<p>Отберём члены каждой периодической серии на промежутке "
        + inline(a.interval)
        + ".</p>"
    )
    for offset, period, start, end, values in a.selections:
        if period.is_Rational is not True or period <= 0:
            raise UnsupportedCondition(
                "the progression step must be a positive rational multiple of pi"
            )
        maximum = int(sp.floor(length / period)) + 1
        if len(values) > maximum:
            raise UnsupportedCondition(
                "the selected members exceed the interval-length bound"
            )
        for text in series_lines(((offset, period),)):
            html += line(text + r",\quad k\in\mathbb Z")
        html += (
            "<p>Разность между соседними членами равна "
            + inline(pi(period))
            + ". Длина промежутка равна "
            + inline(pi(length))
            + "; число членов этой серии в промежутке не превосходит "
            + str(maximum)
            + ".</p>"
        )
        if start > end:
            html += "<p>Членов этой серии в указанном промежутке нет.</p>"
        else:
            html += line(
                r"k\in\{" + ";".join(str(k) for k in range(start, end + 1)) + r"\}"
            )
            html += "<p>Подходят числа:</p>"
            for root in values:
                html += line("x=" + pi(root))
    return html


def finish(a):
    from dataclasses import replace

    from .exam_inverse_bounds import validate
    from .exam_trigonometric import select
    from .exam_trigonometric_affine_selection import combine
    from .exam_trigonometric_inverse import centred

    if sp.cancel(a.scale / sp.pi).is_Rational is True:
        from .exam_trigonometric_pi_scale import finish as finish_pi

        return finish_pi(a)

    series = tuple((q / a.scale - a.translation, p / a.scale) for q, p in a.series)
    if a.shifted_notation:
        series = tuple(s for item in series for s in centred((item,)))
    elif a.selection_method == "inequalities":
        if (
            a.factored_source is not None
            and any(b.original is not None for b in a.branches)
            and not a.poles
        ):
            series = tuple(s for item in series for s in centred((item,)))
        else:
            series = centred(series)
    for bound in a.bounds[:2]:
        validate(bound)
    selected, trace = select(series, a.bounds)
    if a.affine is not None:
        selected = combine(selected, a.affine.roots, a.bounds)
    return replace(a, series=series, selected=selected, selections=trace)


def periodic(residues):
    residues = set(residues)
    if not residues:
        return ()
    shifts = sorted(
        {
            sp.Integer(2),
            *((b - a) % 2 for a in residues for b in residues if (b - a) % 2),
        }
    )
    period = next(p for p in shifts if {(q + p) % 2 for q in residues} == residues)
    return tuple((q, period) for q in sorted({q % period for q in residues}))


def canonical(series):
    from .exam_trigonometric import select

    if any(q.is_Rational is not True or p.is_Rational is not True for q, p in series):
        raise UnsupportedCondition(
            "multiple methods require reviewed rational-pi series"
        )
    return select(series, (sp.Integer(0), sp.Integer(2), True, False))[0]


def root_series(branches, residues, domain, allow_inverse):

    from .exam_trigonometric_inverse import level_series

    if domain is not None:
        series = tuple(s for branch in branches for s in square_series(branch))
    elif (
        all(q.is_Rational for q in residues)
        and len(branches) == 1
        and all(
            power[0] % 2 == 0
            for power in sp.Poly(branches[0].polynomial, branches[0].variable).monoms()
        )
    ):
        series = periodic(residues)
    else:
        series = tuple(
            dict.fromkeys(
                ((q - b.angle_shift) / b.angle_scale, period / b.angle_scale)
                for b in branches
                for v in branch_values(b)
                for q, period in level_series(b.variable, v, allow_inverse)
            )
        )
    return series


def branch_values(branch):
    from functools import cmp_to_key

    from .exam_scalar import compare
    from .exam_trigonometric_compile import C

    values = sorted(
        branch.values, key=cmp_to_key(compare), reverse=branch.variable == C
    )
    return sorted(values, key=lambda v: v != 0) if branch.square_factor else values


def equivalent_series(first, second):
    from .exam_trigonometric import select

    periods = [sp.Rational(p) for _, p in (*first, *second)]
    if not periods or any(p <= 0 for p in periods):
        raise UnsupportedCondition("the methods require positive rational periods")
    period = sp.Rational(
        sp.ilcm(*[p.p for p in periods]), sp.igcd(*[p.q for p in periods])
    )
    if period > 20:
        raise UnsupportedCondition(
            "the common verification period exceeds the reviewed bound"
        )
    return (
        select(first, (0, period, True, False))[0]
        == select(second, (0, period, True, False))[0]
    )


def square_series(branch):
    if not branch.square_level or len(branch.values) != 2 or sum(branch.values) != 0:
        return periodic(branch.residues)
    return tuple((q, sp.S.One) for q in sorted({r % 1 for r in branch.residues}))
