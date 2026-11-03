"""Read complete concurrent internal-bisector questions with fixed point roles."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..isosceles.angle_model import _DEGREES, _value
from ..right.altitude_input import _text
from ..right.altitude_solver import AltitudeSolveError

RULES = {
    "general-triangle-27764-incenter-angle": "between",
    "general-triangle-27778-incenter-bisectors-angle": "foot",
}
_END = "Ответ дайте в градусах."
_RAY = r"([ABC][DEF]|[DEF][ABC])"


@dataclass(frozen=True)
class IncenterAngle:
    mode: str
    frame: str
    values: tuple[sp.Rational, ...]

    def name(self, name):
        mapping = dict(zip("ABC", self.frame)) | {n: n for n in "DEFO"}
        return "".join(mapping[n] for n in name)

    @property
    def c(self):
        return self.values[0] if self.mode == "between" else 180 - sum(self.values)

    @property
    def f(self):
        return 180 - self.values[0] - self.c / 2

    @property
    def answer(self):
        return (
            180 - (180 - self.c) / 2
            if self.mode == "between"
            else 180 - self.values[0] / 2 - self.f
        )

    def require_rule(self, rule):
        if RULES.get(rule) != self.mode:
            raise ContentPlanError(
                "the complete incenter question differs from its registered method"
            )
        return self


def _facts(text):
    angles = {}
    rays = None
    while text.strip(" ,."):
        text = text.lstrip(" ,.")
        angle = re.match(r"угол ([ABC]) равен " + _DEGREES, text)
        construction = re.match(
            _RAY
            + r"(?:\s*, "
            + _RAY
            + r")? и "
            + _RAY
            + r" [—–-] биссектрисы, пересекающиеся в точке O\b",
            text,
        )
        if angle and angle[1] not in angles:
            angles[angle[1]] = _value(angle[2])
            end = angle.end()
        elif construction and rays is None:
            segments = [s for s in construction.groups() if s]
            rays = {
                next(n for n in s if n in "DEF"): next(n for n in s if n in "ABC")
                for s in segments
            }
            if len(rays) != len(segments) or len(set(rays.values())) != len(rays):
                raise ContentPlanError(
                    "the concurrent bisectors must have distinct origins and feet"
                )
            end = construction.end()
        else:
            raise ContentPlanError("an unreviewed or repeated incenter fact remains")
        text = text[end:]
    if rays is None or set(rays) not in ({"D", "E"}, {"D", "E", "F"}):
        raise ContentPlanError(
            "two or three complete internal bisectors through O are required"
        )
    return angles, rays


def read_question(html, source):
    try:
        text = _text(html, source, labels="ABCDEFO")
        if not text.endswith(_END) or text.count("Найдите") != 1:
            raise ContentPlanError(
                "one complete incenter angle question with degree units is required"
            )
        given, request = text[: -len(_END)].strip().split("Найдите")
        prefix = re.match(r"[ВB] треугольнике ABC\s+", given)
        target = re.fullmatch(r"\s*угол ([ABCDEFO]{3})\s*\.\s*", request)
        if prefix is None or target is None or target[1][1] != "O":
            raise ContentPlanError(
                "the complete triangle setup and an angle at O are required"
            )
        angles, rays = _facts(given[prefix.end() :])
        a, b = rays["D"], rays["E"]
        c = (set("ABC") - {a, b}).pop()
        if len(rays) == 2:
            if set(angles) != {c} or set(target[1][::2]) != {a, b}:
                raise ContentPlanError(
                    "the two-bisector angle requires the remaining vertex angle"
                )
            mode, values = "between", (angles[c],)
        else:
            if (
                rays["F"] != c
                or set(angles) != {a, b}
                or set(target[1][::2]) != {a, "F"}
            ):
                raise ContentPlanError(
                    "the bisector-foot angle requires the two reviewed vertex angles"
                )
            mode, values = "foot", (angles[a], angles[b])
            if sum(values) >= 180:
                raise ContentPlanError(
                    "the given angles must define a nondegenerate triangle"
                )
        return IncenterAngle(mode, a + b + c, values)
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
