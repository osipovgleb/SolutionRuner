"""Select progression members using the interval length and the series step."""

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from ..word_problems.water_season_proof import inline
from .exam_trigonometric_compile import T, U
from .exam_trigonometric_style import division


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
    if a.global_radical is not None:
        from .exam_scalar import enclose

        for bound in a.bounds[:2]:
            enclose(bound * sp.pi)
        return replace(a, series=series, selected=(), selections=())
    if a.shifted_notation:
        series = tuple(s for item in series for s in centred((item,)))
    elif a.selection_method == "inequalities":
        if (
            (
                a.factored_source is not None
                or (
                    a.unit_factors is not None
                    and any(b.angle_scale != 1 for b in a.branches)
                )
            )
            and any(b.original is not None for b in a.branches)
            and not a.poles
        ):
            series = tuple(s for item in series for s in centred((item,)))
        else:
            series = centred(series)
    for bound in a.bounds[:2]:
        validate(bound)
    if a.selection_method == "neighbors":
        from .exam_trigonometric_neighbors import certify

        selected, trace = certify(series, a.bounds)
    else:
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

    if domain is not None:
        series = tuple(
            dict.fromkeys(s for branch in branches for s in square_series(branch))
        )
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
                item for b in branches for item in branch_series(b, allow_inverse)
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
    if any(q.is_Rational is not True for q in branch.residues):
        return restricted_series(branch)
    if not branch.square_level or len(branch.values) != 2 or sum(branch.values) != 0:
        return periodic(branch.residues)
    return tuple((q, sp.S.One) for q in sorted({r % 1 for r in branch.residues}))


def restricted_series(branch, value=None):
    from .exam_trigonometric_inverse import angles, level_series

    if branch.angle_scale == 1 and branch.angle_shift:
        return tuple(
            (q - branch.angle_shift, p)
            for v in branch.values
            if value is None or v == value
            for q, p in level_series(branch.variable, v, True)
            if (q - branch.angle_shift) % 2 in branch.residues
        )
    if (
        sp.sympify(branch.angle_scale).is_Integer
        and 1 < branch.angle_scale <= 12
        and not branch.angle_shift
    ):
        return scaled_restricted_series(branch, value)
    if branch.angle_scale != 1 or branch.angle_shift:
        raise UnsupportedCondition(
            "inverse pole filtering requires one unshifted base angle"
        )
    result = []
    for v in branch.values if value is None else (value,):
        candidates = angles(branch.variable, v, True)
        retained = tuple(q for q in candidates if q in branch.residues)
        if retained == candidates:
            result.extend(level_series(branch.variable, v, True))
        else:
            result.extend((q, sp.Integer(2)) for q in retained)
    return tuple(result)


def scaled_restricted_series(branch, value=None):
    from .exam_trigonometric import select
    from .exam_trigonometric_inverse import level_series

    result = []
    for v in branch.values if value is None else (value,):
        for q, p in level_series(branch.variable, v, True):
            item = (q / branch.angle_scale, p / branch.angle_scale)
            orbit = select((item,), (0, 2, True, False))[0]
            retained = tuple(q for q in orbit if q in branch.residues)
            result.extend((item,) if retained == orbit else periodic(retained))
    return tuple(dict.fromkeys(result))


def branch_series(branch, allow_inverse):
    from .exam_trigonometric_compile import C
    from .exam_trigonometric_inverse import level_series

    values = branch_values(branch)
    result = []
    if (
        branch.grouping
        and branch.variable == C
        and {-sp.S.One, sp.S.One} <= set(values)
    ):
        result.append(
            (-branch.angle_shift / branch.angle_scale, 1 / branch.angle_scale)
        )
        values = [v for v in values if abs(v) != 1]
    result.extend(
        ((q - branch.angle_shift) / branch.angle_scale, p / branch.angle_scale)
        for v in values
        for q, p in level_series(branch.variable, v, allow_inverse)
    )
    return tuple(result)


def method_series(
    branches,
    residues,
    compiled,
    domain,
    parent_html,
    style,
):
    from .exam_trigonometric_factor_style import merges_series

    if compiled.original_quotient is not None:
        from .exam_trigonometric_original_quotients import series

        return series(compiled.original_quotient, branches), False, False
    if compiled.strict_quotient is not None:
        from .exam_trigonometric_compile import C
        from .exam_trigonometric_inverse import centred

        series = tuple(dict.fromkeys(s for b in branches for s in restricted_series(b)))
        if compiled.strict_quotient.variable == C:
            series = centred(series)
        return series, False, False
    if compiled.log_product is not None or compiled.log_polynomial is not None:
        if (
            compiled.log_product is not None
            and compiled.log_product.equality is not None
            and compiled.log_product.equality.identity is not None
            and compiled.log_product.equality.identity.base_change is not None
        ):
            return periodic(residues), False, False
        series = tuple(dict.fromkeys(s for b in branches for s in restricted_series(b)))
        if (
            compiled.log_product is not None
            and compiled.log_product.equality is not None
            and compiled.log_product.equality.centre_inverse
        ):
            from .exam_trigonometric_inverse import centred

            series = tuple(s for item in series for s in centred((item,)))
        return series, False, False

    constrained = constrained_series(compiled, branches, residues)
    if constrained is not None:
        return constrained
    if domain is not None and compiled.poles:
        from .exam_trigonometric_inverse import centred

        return (
            tuple(
                s
                for b in branches
                for item in (
                    square_series(b)
                    if compiled.radical_product is not None and b.square_level
                    else restricted_series(b)
                )
                for s in centred((item,))
            ),
            False,
            False,
        )

    if compiled.angle_product is not None and compiled.angle_product.source_poles:
        return (
            tuple(item for b in branches for item in periodic(b.residues)),
            False,
            False,
        )
    if compiled.angle_product is not None and compiled.angle_product.nested:
        from .exam_trigonometric_angle_domain import series as nested_series

        return nested_series(compiled.angle_product, residues), False, False
    if compiled.ratio_product is not None:
        from .exam_trigonometric_ratio_product import series

        return series(branches), False, False
    if (
        style[1] == "inequalities"
        and compiled.scale != 1
        and merges_series(parent_html)
    ):
        return periodic(residues), True, False
    if compiled.fraction is not None and len(compiled.fraction.free_symbols) > 1:
        return tuple(s for b in branches for s in restricted_series(b)), False, False

    preferred, method = style
    allow_inverse = method == "inequalities" or any(
        name in parent_html for name in (r"\arccos", r"\arcsin")
    )
    merged = (
        (
            method == "inequalities"
            and compiled.scale != 1
            and merges_series(parent_html)
        )
        or compiled.square_difference is not None
        or compiled.symmetric is not None
        or (compiled.sum_product is not None and bool(compiled.sum_product.poles))
    )
    dividing = (
        division(parent_html)
        and compiled.homogeneous is None
        and not any(b.original is not None for b in branches)
    )
    if compiled.absolute is not None:
        from .exam_trigonometric_absolute import series as absolute_series

        series = absolute_series(branches[0].values)
    elif dividing:
        from .exam_trigonometric_division import series as division_series

        series = division_series(branches)
    elif merged:
        series = periodic(residues)
    else:
        filtered = domain is not None or (
            compiled.poles
            and compiled.reciprocal is None
            and (preferred not in (T, U) or compiled.angle_product is not None)
        )
        series = root_series(
            branches, residues, filtered if filtered else None, allow_inverse
        )
    return series, merged, dividing


def finalize(result, parent_html):
    from .exam_trigonometric_bounded_log import prepare as bounded_log
    from .exam_trigonometric_centered_power import prepare as centered_power
    from .exam_trigonometric_global_radical import prepare as global_radical
    from .exam_trigonometric_parameters import notation
    from .exam_trigonometric_radical_product import prepare as radical_product
    from .exam_trigonometric_safe_square import prepare as safe_square
    from .exam_trigonometric_square_radical_cases import prepare as square_radicals

    result = notation(centered_power(result, parent_html), parent_html)
    result = radical_product(result, parent_html)
    result = safe_square(result, parent_html)
    result = square_radicals(result, parent_html)
    result = global_radical(result, parent_html)
    return bounded_log(result)


def constrained_series(compiled, branches, residues):
    if compiled.global_radical is not None:
        return (
            root_series(
                branches,
                residues,
                bool(compiled.poles) or None,
                any(q.is_Rational is not True for q in residues),
            ),
            False,
            False,
        )
    if compiled.square_radicals is not None:
        if compiled.square_radicals.method == "linear_absolute":
            return periodic(residues), False, False
        if compiled.square_radicals.method == "absolute_level":
            series = tuple(
                sorted((q - p if q > p / 2 else q, p) for q, p in periodic(residues))
            )
            return series, True, False
    if compiled.radical_equation is not None:
        if any(q.is_Rational is not True for q in residues):
            return (
                tuple(s for branch in branches for s in restricted_series(branch)),
                False,
                False,
            )
        return periodic(residues), False, False
    if compiled.argument_pair is not None:
        from .exam_trigonometric_sine_pair import argument_series

        return argument_series(compiled.argument_pair), False, False
    if compiled.cosine_equality is not None:
        from .exam_trigonometric_cosine_equality import series

        return series(compiled.cosine_equality), False, False
    return None
