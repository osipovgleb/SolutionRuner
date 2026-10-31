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


def homogeneous_first(parent_html):
    for node in BeautifulSoup(parent_html, "html.parser").select("[data-inline-latex]"):
        text = "".join(node["data-inline-latex"].split())
        match = re.search(r"\\(?:sin|cos)x(?:[+-]\\(?:sin|cos)x)?&?=", text)
        if match:
            return "+" in match[0] or "-" in match[0]
    return False


def retain_order(compiled, reduced, branches, parent_html, domain):
    if local_cotangent(parent_html):
        branches = cotangent_branches(branches)
    if (
        reduced != compiled.raw
        and any(b.original is None for b in branches)
        and domain is None
        and not compiled.poles
        and homogeneous_first(parent_html)
    ):
        branches = tuple(sorted(branches, key=lambda b: b.original is None))
        compiled = replace(compiled, raw=reduced, factored_source=compiled.raw)
    return compiled, branches
