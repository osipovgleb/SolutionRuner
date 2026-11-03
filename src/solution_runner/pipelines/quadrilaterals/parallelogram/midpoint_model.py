"""Exact areas and perimeters from complete midpoint questions."""

import re
from dataclasses import dataclass
from itertools import permutations

import sympy as sp

from ...core.errors import ContentPlanError
from ...probability.common import NUMBER
from ...triangles.right.altitude_input import _text
from ...triangles.right.altitude_solver import AltitudeSolveError

TWO_TRAPEZOID = "parallelogram-midpoint-trapezoid-two-methods"
VARIGNON = "parallelogram-midpoint-varignon-area"
TWO_TRIANGLE = "parallelogram-midpoint-triangle-two-methods"
HEIGHT = "parallelogram-665285-midpoint-trapezoid-area"
PERIMETER = "quadrilateral-midpoint-varignon-perimeter"
RULES = {
    TWO_TRAPEZOID: "trapezoid",
    VARIGNON: "varignon",
    TWO_TRIANGLE: "triangle",
    HEIGHT: "trapezoid",
    PERIMETER: "perimeter",
}
FRAMES = tuple(s[i:] + s[:i] for s in ("ABCD", "DCBA") for i in range(4))


@dataclass(frozen=True)
class MidpointArea:
    mode: str
    frame: str
    given: sp.Rational
    target: str
    midpoint: str = ""

    def name(self, text):
        return text.translate(str.maketrans("ABCD", self.frame))

    @property
    def answer(self):
        return (
            self.given
            * {
                "trapezoid": sp.Rational(3, 4),
                "triangle": sp.Rational(1, 4),
                "varignon": sp.Rational(1, 2),
            }[self.mode]
        )


@dataclass(frozen=True)
class MidpointPerimeter:
    diagonals: tuple[sp.Rational, sp.Rational]
    mode = "perimeter"
    frame = "ABCD"

    @property
    def answer(self):
        return sum(self.diagonals)


def _positive(raw):
    value = sp.Rational(raw.replace("{,}", ".").replace(",", "."))
    if value <= 0:
        raise ContentPlanError("the given geometric quantity must be positive")
    return value


def _cyclic(polygon, expected):
    return len(polygon) == len(expected) and any(
        polygon == p[i:] + p[:i]
        for p in (expected, expected[::-1])
        for i in range(len(p))
    )


def read_question(html, source=None):
    identifiers = {"".join(p) for p in permutations("ABCDE", 4)}
    # Four-letter identifiers still pass the same strict markup checks as triangles.
    try:
        text = _text(html, source, labels="ABCDE", extra_identifiers=identifiers)
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
    perimeter = re.fullmatch(
        rf"Диагонали четыр[её]хугольника равны\s+({NUMBER})\s+и\s+({NUMBER})\s*\.\s*"
        r"Найдите периметр четыр[её]хугольника, вершинами которого являются середины сторон данного четыр[её]хугольника\s*\.",
        text,
    )
    if perimeter:
        return MidpointPerimeter(tuple(_positive(v) for v in perimeter.groups()))
    start = re.match(rf"Площадь параллелограмма ABCD равна\s+({NUMBER})\s*\.\s*", text)
    if start is None:
        raise ContentPlanError("one positive complete parallelogram area is required")
    area = _positive(start[1])
    rest = text[start.end() :]
    if re.fullmatch(
        r"Найдите площадь параллелограмма A'B'C'D'\s*,\s*вершинами которого являются середины сторон данного параллелограмма\s*\.",
        rest,
    ):
        return MidpointArea("varignon", "ABCD", area, "A'B'C'D'")
    match = re.fullmatch(
        r"Точка E\s*[—–-]\s*середина стороны ([ABCD]{2})\s*\.\s*Найдите площадь (трапеции|треугольника) ([ABCDE]{3,4})\s*\.",
        rest,
    )
    if match is None:
        raise ContentPlanError(
            "one complete midpoint fact and polygon request are required"
        )
    side, kind, target = match.groups()
    mode = "trapezoid" if kind == "трапеции" else "triangle"
    canonical_side, canonical_target = (
        ("AD", "ABCE") if mode == "trapezoid" else ("CD", "ADE")
    )
    frames = []
    for frame in FRAMES:
        mapping = str.maketrans("ABCD", frame)
        if set(canonical_side.translate(mapping)) == set(side) and _cyclic(
            target, canonical_target.translate(mapping)
        ):
            frames.append(frame)
    if len(frames) != 1:
        raise ContentPlanError(
            "the target must be the stated midpoint triangle or trapezoid"
        )
    return MidpointArea(mode, frames[0], area, target, side)
