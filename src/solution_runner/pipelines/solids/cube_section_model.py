"""Verify the three midpoint edges really form an equilateral corner section."""

import itertools
import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError

HEADER = "ABCDA_1B_1C_1D_1"
VERTICES = {
    "A": (0, 0, 0),
    "B": (1, 0, 0),
    "C": (1, 1, 0),
    "D": (0, 1, 0),
    "A_1": (0, 0, 1),
    "B_1": (1, 0, 1),
    "C_1": (1, 1, 1),
    "D_1": (0, 1, 1),
}
VERTEX = r"[ABCD](?:_1)?"
EDGE = rf"({VERTEX})({VERTEX})"
CLAUSE = rf"точка\s+([KLM])\s*[—–-]\s*середина ребра\s+{EDGE}"
PATTERN = rf"[ВB] кубе\s+{HEADER}\s+{CLAUSE}\s*,\s*{CLAUSE}\s*,\s*{CLAUSE}\s*\.\s*Найдите угол\s+([KLM]{{3}})\s*\.\s*Ответ дайте в градусах\s*\."
IDENTIFIERS = (
    HEADER,
    *(a + b for a, b in itertools.permutations(VERTICES, 2)),
    *("".join(v) for v in itertools.permutations("KLM")),
)


@dataclass(frozen=True)
class CubeSection:
    midpoints: tuple[tuple[str, str, str], ...]
    corner: str
    angle: str
    answer: sp.Integer
    mode: str = "midpoint_section_angle"


def read(text):
    text = re.sub(r"([ABCD])_\{1\}", r"\1_1", text)
    match = re.fullmatch(PATTERN, text)
    if match is None:
        return None
    groups = match.groups()
    midpoints = tuple(tuple(groups[i : i + 3]) for i in (0, 3, 6))
    if {p[0] for p in midpoints} != {"K", "L", "M"} or set(groups[-1]) != {
        "K",
        "L",
        "M",
    }:
        raise ContentPlanError("three distinct section vertices are required")
    corner = set(VERTICES)
    for _, a, b in midpoints:
        if sum(abs(x - y) for x, y in zip(VERTICES[a], VERTICES[b])) != 1:
            raise ContentPlanError("each midpoint must belong to a cube edge")
        corner.intersection_update({a, b})
    edges = {frozenset((a, b)) for _, a, b in midpoints}
    if len(corner) != 1 or len(edges) != 3:
        raise ContentPlanError("three distinct edges must meet at one cube vertex")
    return CubeSection(midpoints, corner.pop(), groups[-1], sp.Integer(60))
