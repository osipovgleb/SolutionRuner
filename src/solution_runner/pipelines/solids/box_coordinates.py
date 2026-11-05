"""Exact vertex-pair geometry and unique positive dimensions of a rectangular box."""

import itertools
import re

import sympy as sp

from ..core.errors import ContentPlanError
from .cube_section_model import HEADER, VERTICES

VERTEX = r"[ABCD](?:_1)?"
SEGMENT = rf"(?:{VERTEX}){{2}}"
IDENTIFIERS = (
    HEADER,
    "ABCD",
    "A_1B_1C_1D_1",
    *VERTICES,
    *(a + b for a, b in itertools.permutations(VERTICES, 2)),
)


def endpoints(segment):
    match = re.fullmatch(rf"({VERTEX})({VERTEX})", segment)
    if match is None or match[1] == match[2]:
        raise ContentPlanError("two distinct canonical box vertices are required")
    return match[1], match[2]


def axes(segment):
    a, b = endpoints(segment)
    return tuple(i for i, (x, y) in enumerate(zip(VERTICES[a], VERTICES[b])) if x != y)


def dimensions(given):
    if len(given) != 3:
        raise ContentPlanError("three independent box measurements are required")
    rows = [[int(i in axes(segment)) for i in range(3)] for segment, _ in given]
    matrix = sp.Matrix(rows)
    if matrix.det() == 0:
        raise ContentPlanError("box measurements do not determine all three dimensions")
    values = []
    for _, v in given:
        if (
            v.is_positive is not True
            or v.is_real is not True
            or v.is_finite is not True
        ):
            raise ContentPlanError(
                "box measurements must be positive finite real values"
            )
        values.append(v * v)
    squares = tuple(sp.simplify(v) for v in matrix.inv() * sp.Matrix(values))
    if any(
        v.is_positive is not True or v.is_real is not True or v.is_finite is not True
        for v in squares
    ):
        raise ContentPlanError(
            "the measurements must yield three positive box dimensions"
        )
    return squares


def squared_length(segment, squares):
    if len(squares) != 3:
        raise ContentPlanError("three squared box dimensions are required")
    return sp.simplify(sum(squares[i] for i in axes(segment)))
