"""Solve each positive power level before applying the original trig constraints."""

from dataclasses import replace
from functools import cmp_to_key

from .exam_trigonometric_compile import C, S


def case_branches(a, level, *, constraints=True, allow_inverse=False):
    if level is None:
        return ()
    from .exam_trigonometric_domain import restrict, without_poles
    from .exam_trigonometric_radical_product import factor_branches

    data = a.power_polynomial
    variable = data.shape.variable
    result = factor_branches(
        variable**data.shape.power - level / data.multiplier, variable, allow_inverse
    )
    if data.shape.power == 2 and data.style.positive_trig_first:
        from .exam_trigonometric_power_polynomial_style import compare_roots

        result = tuple(
            replace(
                b,
                candidates=tuple(
                    sorted(b.candidates, key=cmp_to_key(compare_roots), reverse=True)
                ),
            )
            for b in result
        )
    if constraints:
        if a.domain is not None:
            result = restrict(result, a.domain, a.strict_domain)
        result = without_poles(result, a.poles)
    return result


def branches(a, allow_inverse):
    return tuple(
        b
        for level in a.power_polynomial.levels
        for b in case_branches(a, level, allow_inverse=allow_inverse)
    )


def display_series(variable, rows):
    from .exam_trigonometric_inverse import centred

    if variable in (S, C):
        rows = centred(rows)
    if variable == S and all(q < 0 for q, _ in rows):
        rows = tuple(sorted(rows, key=lambda v: abs(v[0])))
    return rows


def series(a, branches, residues):
    from .exam_trigonometric_selection import periodic, restricted_series

    if a.power_polynomial.shape.power == 2:
        return periodic(residues)
    result = []
    for branch in branches:
        rows = restricted_series(branch)
        result.extend(display_series(branch.variable, rows))
    return tuple(dict.fromkeys(result))
