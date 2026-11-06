"""Keep exact fractions in the four reviewed volume and line-angle methods."""

import sympy as sp


def value(number):
    return sp.latex(sp.simplify(number), inv_trig_style="full")


def bracket(number):
    return r"\left(" + value(number) + r"\right)"
