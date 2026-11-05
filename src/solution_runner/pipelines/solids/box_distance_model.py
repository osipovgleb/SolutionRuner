"""Exact distances and missing edges from actual named rectangular-box segments."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from . import box_coordinates as coordinates
from .box_condition_repairs import restore_html
from .box_geometry_input import assignments, text

DISTANCE = rf"Найдите\s+(квадрат расстояния|расстояние)\s+между вершинами\s+({coordinates.VERTEX})\s+и\s+({coordinates.VERTEX})\s+прямоугольного параллелепипеда,\s*для которого\s+(.+?)\s*\."
SETUP = rf"[ВB] прямоугольном параллелепипеде\s+{coordinates.HEADER}\s+известно, что\s+(.+?)\s*\.\s*Найдите длину\s+(ребра|диагонали)\s+({coordinates.SEGMENT})\s*\."


@dataclass(frozen=True)
class BoxDistance:
    mode: str
    given: tuple[tuple[str, sp.Expr], ...]
    requested: str
    squares: tuple[sp.Expr, ...]
    answer: sp.Expr


def read_question(html, source=None):
    condition = text(restore_html(html), source)
    match = re.fullmatch(DISTANCE, condition)
    if match:
        mode = "distance_squared" if match[1] == "квадрат расстояния" else "distance"
        requested = match[2] + match[3]
        raw = match[4]
    else:
        match = re.fullmatch(SETUP, condition)
        if match is None:
            raise ContentPlanError(
                "one complete named box-distance question is required"
            )
        raw, kind, requested = match.groups()
        size = len(coordinates.axes(requested))
        if size != (1 if kind == "ребра" else 3):
            raise ContentPlanError(
                "the requested box segment contradicts its geometric type"
            )
        mode = "edge" if kind == "ребра" else "diagonal"
    given = assignments(raw)
    squares = coordinates.dimensions(given)
    squared = coordinates.squared_length(requested, squares)
    return BoxDistance(
        mode,
        given,
        requested,
        squares,
        squared if mode == "distance_squared" else sp.sqrt(squared),
    )
