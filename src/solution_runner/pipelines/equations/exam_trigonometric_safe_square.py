"""Preserve certified parent families and their roles after safe squaring."""

import re
from dataclasses import replace
from html import escape

from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import S
from .exam_trigonometric_parameters import affine_families
from .exam_trigonometric_selection import equivalent_series


def parameter_roles(html):
    source = affine_families(html)
    if len({name for _, _, name in source}) <= 1:
        return ()
    soup = BeautifulSoup(html, "html.parser")
    first = soup.find("li", attrs={"data-list-marker": "а)"})
    if first is None:
        raise UnsupportedCondition("distinct square-branch parameters require part a")
    formulas = [n["data-inline-latex"] for n in first.select("[data-inline-latex]")]
    if not formulas:
        raise UnsupportedCondition("the parent must declare its final square branches")
    final = re.split(r"\\(?:iff|Leftrightarrow)", formulas[-1])[-1]
    accepted = affine_families(
        '<span data-inline-latex="' + escape(final) + '"></span>'
    )
    if (
        len(accepted) != 2
        or accepted[0][0].is_Integer is not True
        or accepted[1][0].is_Integer is not False
        or any(p != 2 for _, p, _ in accepted)
        or accepted[0][2] == accepted[1][2]
    ):
        raise UnsupportedCondition(
            "the parent must bind zero and nonzero sine branches"
        )
    rejected = {name for _, _, name in source} - {n for _, _, n in accepted}
    if len(rejected) != 1:
        raise UnsupportedCondition("one rejected nominal branch parameter is required")
    return accepted[0][2], accepted[1][2], rejected.pop()


def prepare(a, parent_html):
    if a.radical_equation is None or a.radical_equation.kind != "safe_square":
        return a
    from .exam_trigonometric import select

    roles = parameter_roles(parent_html)
    if roles:
        zeros = tuple((q, p) for q, p in a.series if q.is_Integer is True)
        others = tuple((q, p) for q, p in a.series if q.is_Integer is not True)
        if (
            len(zeros) != 1
            or len(others) != 1
            or len(a.branches) != 1
            or a.branches[0].variable != S
            or 0 not in a.branches[0].values
            or any(p != 2 for _, p in a.series)
        ):
            raise UnsupportedCondition("the child's two sine branch roles changed")
        source = tuple(
            (q % 2 if q.is_Integer else (q % 2) - (2 if q % 2 > 1 else 0), p)
            for q, p in (*zeros, *others)
        )
        parameters = roles[:2]
    else:
        formulas = BeautifulSoup(parent_html, "html.parser").select(
            "[data-inline-latex]"
        )
        ordered_source = tuple(
            f for node in formulas for f in affine_families(str(node))
        )
        source = tuple(
            reversed(
                tuple(
                    dict.fromkeys(
                        (q, p)
                        for q, p, _ in reversed(ordered_source)
                        if equivalent_series((*a.series, (q, p)), a.series)
                    )
                )
            )
        )
        if (
            not source
            and a.sine_inverse
            and any(q.is_Rational is not True for q, _ in a.series)
        ):
            source = a.series
        parameters = ()
    if not source or not equivalent_series(source, a.series):
        raise UnsupportedCondition(
            "the parent families must cover the complete filtered solution"
        )
    selected, trace = select(source, a.bounds)
    return replace(
        a,
        series=source,
        selected=selected,
        selections=trace,
        family_parameters=parameters,
        series_aligned=source != a.series,
        radical_equation=replace(a.radical_equation, parameters=roles),
    )
