"""Read complete exterior-angle and single-bisector questions without numeric fallback."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..isosceles.angle_model import _DEGREES, _value
from ..right.altitude_input import _text
from ..right.altitude_solver import AltitudeSolveError

RULES = {
    "general-triangle-27743-exterior-angle": "external",
    "general-triangle-27758-bisector-angle": "bisector_base",
    "general-triangle-27759-bisector-exterior-angle": "bisector_external",
}
_END = "Ответ дайте в градусах."


@dataclass(frozen=True)
class SimpleAngle:
    mode: str
    frame: str
    first: sp.Rational
    second: sp.Rational

    def name(self, name):
        mapping = dict(zip("ABCD", self.frame + "D"))
        return "".join(mapping[c] for c in name)

    @property
    def angles(self):
        canonical = (
            (self.first, 180 - self.second, self.second - self.first)
            if self.mode == "external"
            else (2 * self.second, 180 - 2 * self.second - self.first, self.first)
        )
        return dict(zip(self.frame, canonical))

    @property
    def answer(self):
        return {
            "external": self.angles[self.frame[2]],
            "bisector_base": self.angles[self.frame[1]],
            "bisector_external": self.first + self.second,
        }[self.mode]

    def require_rule(self, rule):
        if RULES.get(rule) != self.mode:
            raise ContentPlanError(
                "the complete angle question differs from its registered method"
            )
        return self


def _facts(text):
    angles = []
    bisector = None
    while text.strip(" ,."):
        text = text.lstrip(" ,.")
        half = re.match(r"([ABC]D|D[ABC]) [—–-] биссектриса\b", text)
        angle = re.match(r"угол ([ABCD]{3}|[ABC]) равен " + _DEGREES, text)
        exterior = re.match(
            r"[Вв]нешний угол при вершине ([ABC]) равен " + _DEGREES, text
        )
        if half and bisector is None:
            bisector = half[1].replace("D", "")
            end = half.end()
        elif angle or exterior:
            match = angle or exterior
            angles.append((bool(exterior), match[1], _value(match[2])))
            end = match.end()
        else:
            raise ContentPlanError("an unreviewed or repeated angle fact remains")
        text = text[end:]
    if len(angles) != 2:
        raise ContentPlanError("exactly two independent angle facts are required")
    return bisector, angles


def _external(angles, target):
    internals = [g for g in angles if not g[0] and len(g[1]) == 1]
    externals = [g for g in angles if g[0]]
    if len(internals) != 1 or len(externals) != 1 or len(target) != 1:
        raise ContentPlanError(
            "one internal and one exterior angle must determine the third angle"
        )
    _, a, first = internals[0]
    _, b, second = externals[0]
    if set(a + b + target) != set("ABC"):
        raise ContentPlanError("the given and requested vertices must be distinct")
    return SimpleAngle("external", a + b + target, first, second)


def _bisector(apex, angles, target):
    if any(g[0] for g in angles):
        raise ContentPlanError("the bisector method requires two internal angles")
    singles = [g for g in angles if len(g[1]) == 1]
    halves = [g for g in angles if len(g[1]) == 3]
    if len(singles) != 1 or len(halves) != 1:
        raise ContentPlanError(
            "one triangle angle and one half of the bisected angle are required"
        )
    _, c, first = singles[0]
    _, half, second = halves[0]
    if c == apex or half[1] != apex or "D" not in half[::2] or len(set(half)) != 3:
        raise ContentPlanError("the stated half-angle must lie at the bisector origin")
    other = (set("ABC") - {apex, c}).pop()
    if set(half[::2]) not in ({"D", c}, {"D", other}):
        raise ContentPlanError(
            "the half-angle must use a triangle side and the bisector"
        )
    if target == other:
        mode = "bisector_base"
    elif len(target) == 3 and target[1] == "D" and set(target[::2]) == {apex, other}:
        mode = "bisector_external"
    else:
        raise ContentPlanError(
            "the requested angle differs from the reviewed bisector methods"
        )
    return SimpleAngle(mode, apex + other + c, first, second)


def read_question(html, source):
    try:
        text = _text(html, source, labels="ABCD")
        if not text.endswith(_END) or text.count("Найдите") != 1:
            raise ContentPlanError(
                "one complete angle question with degree units is required"
            )
        given, request = text[: -len(_END)].strip().split("Найдите")
        prefix = re.match(r"[ВB] треугольнике ABC\s+", given)
        target = re.fullmatch(r"\s*угол ([ABC]|[ABC]D[ABC])\s*\.\s*", request)
        if prefix is None or target is None:
            raise ContentPlanError(
                "the complete named triangle and angle request are required"
            )
        apex, angles = _facts(given[prefix.end() :])
        model = (
            _external(angles, target[1])
            if apex is None
            else _bisector(apex, angles, target[1])
        )
        if any(not 0 < v < 180 for v in model.angles.values()):
            raise ContentPlanError(
                "the given angles must define a nondegenerate triangle"
            )
        return model
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
