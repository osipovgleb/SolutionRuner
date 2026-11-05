"""Whole-question rectangular-box quantities with positive realizable dimensions."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from ..equations.power_arithmetic import ScalarParser
from ..probability.common import UnsupportedCondition
from ..triangles.right.altitude_input import _text
from ..triangles.right.altitude_solver import AltitudeSolveError

BOX = "прямоугольного параллелепипеда"
TWO = rf"Два ребра {BOX}, выходящие из одной вершины, равны\s+(.+?)\s*\.\s*"
THREE = rf"(?:Три ребра|Ребра) {BOX}, выходящие из одной вершины, равны\s+(.+?)\s*\.\s*"
SURFACE = r"Площадь поверхности (?:этого )?параллелепипеда равна\s+(.+?)\s*\.\s*"
VOLUME = r"Объем параллелепипеда равен\s+(.+?)\s*\.\s*"
DIAGONAL = r"Диагональ параллелепипеда равна\s+(.+?)\s*\.\s*"
FIND = r"Найди(?:те)? "
PATTERNS = {
    "square_face_volume": r"Одна из граней прямоугольного параллелепипеда\s*[—–-]\s*квадрат\.\s*Диагональ параллелепипеда равна\s+(.+?)\s+и образует с плоскостью этой грани угол\s+(.+?)°\s*\.\s*Найдите объем параллелепипеда\s*\.",
    "edge_from_surface": TWO
    + SURFACE
    + FIND
    + r"третье ребро, выходящее из той же вершины\s*\.",
    "diagonal_from_surface": TWO + SURFACE + FIND + r"его диагональ\s*\.",
    "volume_from_face": rf"Площадь грани {BOX} равна\s+(.+?)\s*\.\s*Ребро, перпендикулярное этой грани, равно\s+(.+?)\s*\.\s*"
    + FIND
    + r"объем параллелепипеда\s*\.",
    "face_from_volume": rf"Объем {BOX} равен\s+(.+?)\s*\.\s*Одно из его ребер равно\s+(.+?)\s*\.\s*"
    + FIND
    + r"площадь грани параллелепипеда, перпендикулярной этому ребру\s*\.",
    "edge_from_face": rf"Объем {BOX} равен\s+(.+?)\s*\.\s*Площадь одной его грани равна\s+(.+?)\s*\.\s*"
    + FIND
    + r"ребро параллелепипеда, перпендикулярное этой грани\s*\.",
    "edge_from_volume": TWO
    + VOLUME
    + FIND
    + r"третье ребро параллелепипеда, выходящее из той же вершины\s*\.",
    "cube_edge_from_edges": THREE + FIND + r"ребро равновеликого ему куба\s*\.",
    "volume_from_diagonal": TWO + DIAGONAL + FIND + r"объем параллелепипеда\s*\.",
    "diagonal_from_volume": TWO + VOLUME + FIND + r"его диагональ\s*\.",
    "surface_from_edges": THREE + FIND + r"его площадь поверхности\s*\.",
    "surface_from_diagonal": TWO
    + DIAGONAL
    + FIND
    + r"площадь поверхности параллелепипеда\s*\.",
    "surface_from_volume": TWO + VOLUME + FIND + r"площадь его поверхности\s*\.",
}
FACE_MODES = {"volume_from_face", "face_from_volume", "edge_from_face"}
THREE_MODES = {"cube_edge_from_edges", "surface_from_edges"}
SURFACE_MODES = {"edge_from_surface", "diagonal_from_surface"}
DIAGONAL_MODES = {"volume_from_diagonal", "surface_from_diagonal"}


@dataclass(frozen=True)
class BoxQuantity:
    mode: str
    given: tuple[sp.Expr, ...]
    edges: tuple[sp.Expr, ...]
    answer: sp.Expr


def _givens(mode, groups):
    if mode in FACE_MODES or mode == "square_face_volume":
        raw = groups
    else:
        parts = re.split(r",\s+|\s+и\s+", groups[0])
        if len(parts) != (3 if mode in THREE_MODES else 2):
            raise ContentPlanError("the box edge list must have unambiguous separators")
        raw = (*parts, *groups[1:])
    values = tuple(ScalarParser(v).parse() for v in raw)
    if any(
        v.is_real is not True or v.is_finite is not True or v.is_positive is not True
        for v in values
    ):
        raise ContentPlanError("box measurements must be positive finite real values")
    return values


def _quantity(mode, v):
    if mode == "square_face_volume":
        d, angle = v
        if angle.is_Rational is not True or (90 - angle).is_positive is not True:
            raise ContentPlanError(
                "the diagonal must form an explicit acute degree angle"
            )
        height = sp.simplify(d * sp.sin(angle * sp.pi / 180))
        face_diagonal = sp.simplify(d * sp.cos(angle * sp.pi / 180))
        if height.has(sp.sin, sp.cos) or face_diagonal.has(sp.sin, sp.cos):
            raise ContentPlanError(
                "the parent method requires exact elementary trigonometric values"
            )
        a = sp.simplify(face_diagonal / sp.sqrt(2))
        return (a, a, height), sp.simplify(face_diagonal**2 * height / 2)
    if mode in FACE_MODES:
        return (), sp.simplify(
            v[0] * v[1] if mode == "volume_from_face" else v[0] / v[1]
        )
    a, b, last = v
    if mode in THREE_MODES:
        c = last
    elif mode in SURFACE_MODES:
        if sp.simplify(last - 2 * a * b).is_positive is not True:
            raise ContentPlanError("the given surface must leave a positive third edge")
        c = sp.simplify((last / 2 - a * b) / (a + b))
    elif mode in DIAGONAL_MODES:
        square = sp.simplify(last**2 - a * a - b * b)
        if square.is_positive is not True:
            raise ContentPlanError("the diagonal must leave a positive third edge")
        c = sp.sqrt(square)
    else:
        c = sp.simplify(last / (a * b))
    volume = sp.simplify(a * b * c)
    surface = sp.simplify(2 * (a * b + a * c + b * c))
    diagonal = sp.sqrt(sp.simplify(a * a + b * b + c * c))
    answer = {
        "edge_from_surface": c,
        "diagonal_from_surface": diagonal,
        "edge_from_volume": c,
        "cube_edge_from_edges": volume ** sp.Rational(1, 3),
        "volume_from_diagonal": volume,
        "diagonal_from_volume": diagonal,
        "surface_from_edges": surface,
        "surface_from_diagonal": surface,
        "surface_from_volume": surface,
    }[mode]
    return (a, b, c), sp.simplify(answer)


def read_question(html, source=None):
    if not isinstance(html, str):
        raise ContentPlanError("complete box condition HTML is required")
    if re.search(r"<img\b", html, re.IGNORECASE) and (
        not isinstance(source, str) or not source
    ):
        raise ContentPlanError("a reviewed box condition image is required")
    try:
        text = _text(html, source, labels="ABCDabcd").replace("ё", "е")
        for mode, pattern in PATTERNS.items():
            match = re.fullmatch(pattern, text)
            if match is None:
                continue
            given = _givens(mode, match.groups())
            edges, answer = _quantity(mode, given)
            return BoxQuantity(mode, given, edges, answer)
    except (UnsupportedCondition, AltitudeSolveError) as exc:
        raise ContentPlanError(str(exc)) from exc
    raise ContentPlanError("one complete reviewed rectangular-box question is required")
