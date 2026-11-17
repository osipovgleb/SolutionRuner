"""Render exact trigonometric expressions and periodic root families."""

from functools import cmp_to_key

import sympy as sp

from .exam_trigonometric import C, S, T, U
from .exam_trigonometric_inverse import compare_q
from .exam_trigonometric_inverse import display_angle as complementary_angle

K = sp.Symbol("k", integer=True)


def formula(value, angle="x"):
    return sp.latex(
        value,
        symbol_names={
            S: r"(\sin " + angle + ")",
            C: r"(\cos " + angle + ")",
            T: r"(\tg " + angle + ")",
            U: r"(\ctg " + angle + ")",
        },
    )


def pi(q, *, sine_inverse=False):
    angle = sp.expand(q * sp.pi)
    return sp.latex(
        complementary_angle(angle) if sine_inverse else angle, inv_trig_style="full"
    )


def series_lines(series, *, sine_inverse=False):
    remaining = list(series)
    result = []
    while remaining:
        offset, period = remaining.pop(0)
        pair = next(
            (
                (a, p)
                for a, p in remaining
                if p == period and (a + offset == period or a + offset == 0)
            ),
            None,
        )
        if pair:
            remaining.remove(pair)
            angle = min((abs(offset), abs(pair[0])), key=cmp_to_key(compare_q))
            text = pi(angle, sine_inverse=sine_inverse)
            if sp.expand(angle * sp.pi).is_Add:
                text = r"\left(" + text + r"\right)"
            result.append("x=" + r"\pm" + text + "+" + sp.latex(period * sp.pi * K))
        else:
            result.append(
                "x="
                + sp.latex(
                    sp.expand(
                        (
                            complementary_angle(sp.expand(offset * sp.pi))
                            if sine_inverse
                            else offset * sp.pi
                        )
                        + period * sp.pi * K
                    ),
                    inv_trig_style="full",
                )
            )
    return tuple(result)
