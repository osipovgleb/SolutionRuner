"""Keep the parent's square-level method and its signed final ratio families."""

import re
from dataclasses import replace

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S, T, U
from .exam_trigonometric_parameters import affine_families
from .power_arithmetic import ScalarParser, clean


def reviewed(parent_html):
    for node in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]"):
        text = clean(node["data-inline-latex"])
        for match in re.finditer(r"\\(sin|cos|tg|ctg)\^\{?2\}?x&?=", text):
            right = re.split(
                r"\\\\|\\(?:end|quad|iff|Leftrightarrow)|,",
                text[match.end() :],
                maxsplit=1,
            )[0].removesuffix(".")
            try:
                value = ScalarParser(right).parse()
            except UnsupportedCondition:
                continue
            if not value.free_symbols and value.is_positive is True:
                return {"sin": S, "cos": C, "tg": T, "ctg": U}[match[1]]
    return None


def mark(branches, parent_html, fraction):
    variable = reviewed(parent_html) if fraction is not None else None
    if len(branches) != 1 or variable is None:
        return branches
    b = branches[0]
    if (
        b.variable != variable
        or sp.degree(b.polynomial, variable) != 2
        or b.polynomial.coeff(variable) != 0
    ):
        return branches
    return (replace(b, square_level=True),)


def notation(a, parent_html):
    from .exam_trigonometric import select
    from .exam_trigonometric_selection import equivalent_series

    if (
        a.fraction is None
        or len(a.branches) != 1
        or not a.branches[0].square_level
        or a.branches[0].variable not in (T, U)
    ):
        return a, ()
    declared = affine_families(parent_html)
    if (
        len(declared) != len(a.series)
        or len(declared) != 2
        or any(p != 2 for _, p, _ in declared)
        or any(p != 2 or q.is_Rational is not True for q, p in a.series)
    ):
        return a, ()
    source = tuple((q, p) for q, p, _ in declared)
    if equivalent_series(source, a.series):
        wanted = source
    else:
        wanted = tuple((q % p - p if q % p > p / 2 else q % p, p) for q, p in a.series)
        if all(q >= 0 for q, _, _ in declared):
            wanted = tuple(
                sorted(
                    wanted,
                    key=lambda item: abs(item[0]),
                    reverse=abs(declared[0][0]) > abs(declared[1][0]),
                )
            )
        else:
            wanted = tuple(sorted(wanted, reverse=declared[0][0] > declared[1][0]))
    if not equivalent_series(wanted, a.series):
        raise UnsupportedCondition(
            "the signed final families must preserve every computed root"
        )
    selected, trace = select(wanted, a.bounds)
    return replace(
        a,
        series=wanted,
        selected=selected,
        selections=trace,
        series_aligned=wanted != a.series,
    ), tuple(name for _, _, name in declared)
