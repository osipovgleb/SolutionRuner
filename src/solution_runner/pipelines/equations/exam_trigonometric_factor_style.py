"""Retain the parent's common factor and a local cotangent substitution."""

import re
from collections import Counter
from dataclasses import replace

import sympy as sp
from bs4 import BeautifulSoup

from .exam_trigonometric_compile import C, S, T, U


def common_factor(parent_html):
    soup = BeautifulSoup(parent_html, "html.parser")
    if "группируем" not in soup.get_text(" ").replace("\xad", "").lower():
        return None, False
    for node in soup.select("[data-inline-latex]"):
        text = "".join(node["data-inline-latex"].split())
        groups = Counter(
            re.findall(r"\(([^()]*(?:\\sin|\\cos|\\tg)(?:\^\{?2\}?)?x[^()]*)\)", text)
        )
        for group, count in groups.items():
            if count > 1:
                match = re.search(r"\\(sin|cos|tg)(\^\{?2\}?)?x", group)
                return {"sin": S, "cos": C, "tg": T}[match[1]], bool(match[2])
    return None, False


def mark_grouping(branches, parent_html):
    from .exam_trigonometric_style import grouping_method

    common, quadratic = common_factor(parent_html)
    if not grouping_method(parent_html) and common is None:
        return branches
    return tuple(
        replace(
            b,
            grouping=(common is None or b.variable == common),
            quadratic_common=quadratic,
        )
        for b in branches
    )


def local_cotangent(parent_html):
    from .exam_trigonometric_style import cotangent_method

    if not cotangent_method(parent_html):
        return False
    return any(
        r"\cosx=0" in "".join(n["data-inline-latex"].split())
        for n in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]")
    )


def cotangent_branches(branches):
    from .exam_trigonometric_inverse import angles, ordered

    result = []
    for b in branches:
        if b.variable == T and b.original is not None and not b.angle_shift:
            a, c = b.original.coeff(S), b.original.coeff(C)
            value = sp.cancel(-a / c)
            b = replace(
                b,
                variable=U,
                polynomial=U - value,
                candidates=(value,),
                values=(value,),
                residues=ordered(angles(U, value)),
            )
        result.append(b)
    return tuple(sorted(result, key=lambda b: b.original is not None))
