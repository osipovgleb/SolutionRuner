"""Read complete direct, inverse and trapezoid questions about one midline."""

import re
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ..right.altitude_input import _text
from ..right.altitude_solver import AltitudeSolveError, _parse_positive_value

RULES = {
    "general-triangle-27592-midline-area": "small",
    "general-triangle-317337-midline-small-area-to-total": "total",
    "general-triangle-319058-midline-trapezoid-area": "trapezoid",
}


@dataclass(frozen=True)
class MidlineArea:
    mode: str
    vertex: str
    given: sp.Expr

    @property
    def mapping(self):
        p, q = sorted(set("ABC") - {self.vertex})
        return dict(zip("ABCDE", p + q + self.vertex + "DE"))

    def name(self, canonical):
        return "".join(self.mapping[c] for c in canonical)

    @property
    def small(self):
        return self.given if self.mode == "total" else self.given / 4

    @property
    def total(self):
        return self.given * 4 if self.mode == "total" else self.given

    @property
    def answer(self):
        return {
            "small": self.small,
            "total": self.total,
            "trapezoid": self.total - self.small,
        }[self.mode]

    def require_rule(self, rule):
        if RULES.get(rule) != self.mode:
            raise ContentPlanError(
                "the complete midline question differs from its rule"
            )
        return self


def _area(raw):
    value = _parse_positive_value(raw)
    if value.is_Rational is not True:
        raise ContentPlanError("a positive exact rational area is required")
    return value


def _stream(html, source):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("var"):
        name = tag.get_text()
        if len(name) == 4:
            if (
                set(tag.attrs) != {"data-math-identifier"}
                or tag["data-math-identifier"] != name
                or not re.fullmatch(r"[ABCDE]{4}", name)
            ):
                raise ContentPlanError("the trapezoid identifier is ambiguous")
            tag.replace_with(name)
    return _text(str(soup), source, labels="ABCDE")


def _direct(given, kind, target):
    match = re.fullmatch(
        r"Площадь треугольника ABC равна (.+?)[,.] DE [—–-] средняя линия"
        r"(?:, параллельная стороне ([ABC]{2}))?\s*\.\s*",
        given,
    )
    if match is None:
        raise ContentPlanError(
            "one total area and one complete midline fact are required"
        )
    if kind == "треугольника" and len(target) == 3 and set(target) & set("ABC"):
        vertex = next(v for v in target if v in "ABC")
        if set(target) != {vertex, "D", "E"}:
            raise ContentPlanError("the small triangle must use both midline endpoints")
        mode = "small"
    elif kind == "трапеции" and match[2]:
        base = "".join(sorted(match[2]))
        if len(set(base)) != 2:
            raise ContentPlanError("the midline must be parallel to one triangle side")
        vertex = (set("ABC") - set(base)).pop()
        polygon = base + "ED"
        rotations = {polygon[i:] + polygon[:i] for i in range(4)}
        if target not in rotations | {s[::-1] for s in rotations}:
            raise ContentPlanError("the trapezoid vertices must follow its boundary")
        mode = "trapezoid"
    else:
        raise ContentPlanError(
            "one small triangle or midline trapezoid must be requested"
        )
    if match[2] and set(match[2]) != set("ABC") - {vertex}:
        raise ContentPlanError(
            "the reviewed similarity requires the opposite parallel side"
        )
    return MidlineArea(mode, vertex, _area(match[1]))


def read_question(html, source):
    try:
        text = _stream(html, source)
        if text.count("Найдите") != 1:
            raise ContentPlanError("one complete midline area question is required")
        given, request = text.split("Найдите")
        target = re.fullmatch(
            r"\s*площадь (треугольника|трапеции) ([ABCDE]{3,4})\s*\.\s*", request
        )
        if target is None:
            raise ContentPlanError("the complete area request must be reviewed")
        inverse = re.fullmatch(
            r"[ВB] треугольнике ABC (?:отрезок )?DE [—–-] средняя линия\. "
            r"Площадь треугольника ([ABC][DE]{2}) равна (.+?)\.\s*",
            given,
        )
        if inverse:
            if (target[1], target[2]) != ("треугольника", "ABC") or set(
                inverse[1][1:]
            ) != {"D", "E"}:
                raise ContentPlanError(
                    "the inverse midline question requires the whole triangle"
                )
            return MidlineArea("total", inverse[1][0], _area(inverse[2]))
        return _direct(given, target[1], target[2])
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
