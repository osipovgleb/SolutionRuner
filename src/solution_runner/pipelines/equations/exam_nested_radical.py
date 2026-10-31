"""A symmetric nested-root sum has an interval, with interval or point queries."""

import re
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition
from .exam_input import endpoint, read_interval, read_parts, repair
from .exam_scalar import compare
from .power_arithmetic import ScalarParser, clean


@dataclass(frozen=True)
class Analysis:
    coefficient: sp.Expr
    centre: sp.Expr
    interval: str | None
    bounds: tuple | None
    points: tuple
    selected: tuple | None
    membership: tuple


def analyze(formula, second, parent_html):
    match = re.fullmatch(
        r"\\sqrt\{x\+(?P<k>\d+(?:\.\d+)?)\\sqrt\{x-(?P<c>\d+(?:\.\d+)?)\}\}\+\\sqrt\{x-(?P=k)\\sqrt\{x-(?P=c)\}\}=(?P=k)",
        clean(formula),
    )
    if not match:
        raise UnsupportedCondition(
            "one complete symmetric nested-root equation is required"
        )
    k, c = (ScalarParser(match[key]).parse() for key in ("k", "c"))
    if k <= 0 or c <= 0 or k * k != 4 * c:
        raise UnsupportedCondition(
            "both nested radicands must become exact complete squares"
        )
    soup = BeautifulSoup(parent_html, "html.parser")
    sections = soup.find_all("section", recursive=False)
    titles = [
        s.get("data-solution-title", "").replace("ё", "е").lower() for s in sections
    ]
    text = soup.get_text(" ", strip=True).replace("\xad", "").replace("ё", "е").lower()
    if titles != ["решение", "приведем другое решение."] or not all(
        s in text
        for s in ("замену переменной", "неположительных", "возведем их в квадрат")
    ):
        raise UnsupportedCondition(
            "both original methods in their two ordered sections are required"
        )
    point_query = re.fullmatch(
        r"Определите, являются ли решениями уравнения числа (.+?) и (.+?)\.?", second
    )
    if point_query:
        points = tuple(endpoint(t) for t in point_query.groups())
        membership = tuple(
            compare(t, c) >= 0 and compare(t, 2 * c) <= 0 for t in points
        )
        return Analysis(k, c, None, None, points, None, membership)
    interval, bounds = read_interval(second)
    lo, hi, lc, uc = bounds
    left = lo if compare(lo, c) >= 0 else c
    right = hi if compare(hi, 2 * c) <= 0 else 2 * c
    left_closed = lc if compare(left, lo) == 0 else True
    right_closed = uc if compare(right, hi) == 0 else True
    order = compare(left, right)
    selected = (
        None
        if order > 0 or (order == 0 and not (left_closed and right_closed))
        else (left, right, left_closed, right_closed)
    )
    return Analysis(k, c, interval, bounds, (), selected, ())


def build_context_repair_plan(context, *, parent_solution_html=""):
    from .exam_nested_radical_proof import render

    parts, formula, second = read_parts(context)
    a = analyze(formula, second, parent_solution_html)
    return repair(parts, *render(a))
