"""Read complete equal-side angle constructions and keep their distinct methods."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..isosceles.angle_model import _value
from ..right.altitude_input import _text
from ..right.altitude_solver import AltitudeSolveError
from .altitude_quad_model import _DEGREES

RULES = {
    "general-triangle-27769-extension-isosceles-angle": "extension",
    "general-triangle-27776-bisector-congruent-angle": "congruent",
    "general-triangle-27777-exterior-bisector-isosceles-angle": "exterior",
}


@dataclass(frozen=True)
class EqualSideAngle:
    mode: str
    frame: str
    values: tuple[sp.Rational, sp.Rational]

    def name(self, text):
        names = dict(zip("ABC", self.frame)) | {n: n for n in "DE"}
        return "".join(names[n] for n in text)

    @property
    def alpha(self):
        return 180 - sum(self.values) if self.mode == "congruent" else self.values[0]

    @property
    def beta(self):
        if self.mode == "extension":
            return 180 - sum(self.values)
        return self.values[0] if self.mode == "congruent" else self.values[1]

    @property
    def gamma(self):
        return 180 - sum(self.values) if self.mode == "exterior" else self.values[1]

    @property
    def answer(self):
        if self.mode == "extension":
            return self.beta / 2
        return (
            self.gamma - self.beta
            if self.mode == "congruent"
            else abs(self.beta - self.alpha)
        )

    def require_rule(self, rule):
        if RULES.get(rule) != self.mode:
            raise ContentPlanError(
                "the complete construction differs from the registered equal-side method"
            )
        return self


def _extension(text, request, angles):
    match = re.fullmatch(
        r"На продолжении стороны (?P<a>[ABC])(?P<b>[ABC]) за точку (?P=b) отложен отрезок (?P=b)D, равный стороне (?P<side>[ABC]{2})\.",
        text,
    )
    target = re.fullmatch(r"\s*угол D треугольника ([ABCD]{3})\.\s*", request)
    if match is None or target is None or match["a"] == match["b"]:
        raise ContentPlanError(
            "one complete external equal-side construction is required"
        )
    a, b = match["a"], match["b"]
    c = (set("ABC") - {a, b}).pop()
    if (
        set(angles) != {a, c}
        or match["side"] not in {b + c, c + b}
        or set(target[1]) != {b, c, "D"}
    ):
        raise ContentPlanError(
            "the extended side, equal segment or requested triangle changed"
        )
    return EqualSideAngle("extension", a + b + c, (angles[a], angles[c]))


def _congruent(text, request, angles):
    match = re.fullmatch(
        r"(?P<a>[ABC])D [—–-] биссектриса, E [—–-] такая точка на (?P<side>[ABC]{2}), что (?P<first>[ABCDE]{2})\s*=\s*(?P<second>[ABCDE]{2})\.",
        text,
    )
    target = re.fullmatch(r"\s*угол ([ABCDE]{3})\.\s*", request)
    if match is None or target is None:
        raise ContentPlanError(
            "one complete internal-bisector equal-side construction is required"
        )
    a, side = match["a"], set(match["side"])
    if len(side) != 2 or a not in side:
        raise ContentPlanError("the equal segment must lie on the bisected vertex side")
    b = (side - {a}).pop()
    c = (set("ABC") - side).pop()
    equality = {frozenset(match["first"]), frozenset(match["second"])}
    if (
        equality != {frozenset(a + "E"), frozenset(a + c)}
        or set(angles) != {b, c}
        or target[1] not in {b + "DE", "ED" + b}
    ):
        raise ContentPlanError(
            "the equal sides or requested congruent-triangle angle changed"
        )
    if angles[c] <= angles[b]:
        raise ContentPlanError("the equal point E must lie strictly inside the side AB")
    return EqualSideAngle("congruent", a + b + c, (angles[b], angles[c]))


def _exterior(text, request, angles):
    match = re.fullmatch(
        r"(?P<c>[ABC])D [—–-] биссектриса внешнего угла при вершине (?P=c), причем точка D лежит на прямой (?P<base>[ABC]{2})\. "
        r"На продолжении стороны (?P<a>[ABC])(?P=c) за точку (?P=c) выбрана такая точка E, что (?P<first>[ABCDE]{2})\s*=\s*(?P<second>[ABCDE]{2})\.",
        text,
    )
    target = re.fullmatch(r"\s*угол ([ABCDE]{3})\.\s*", request)
    if match is None or target is None or match["a"] == match["c"]:
        raise ContentPlanError(
            "one complete exterior-bisector equal-side construction is required"
        )
    a, c = match["a"], match["c"]
    b = (set("ABC") - {a, c}).pop()
    equality = {frozenset(match["first"]), frozenset(match["second"])}
    if (
        set(match["base"]) != {a, b}
        or equality != {frozenset(c + "E"), frozenset(c + b)}
        or set(angles) != {a, b}
        or target[1] not in {b + "DE", "ED" + b}
    ):
        raise ContentPlanError(
            "the exterior bisector, equal extension or requested rays changed"
        )
    if angles[a] == angles[b]:
        raise ContentPlanError(
            "the exterior bisector is parallel to AB and has no finite point D"
        )
    return EqualSideAngle("exterior", a + b + c, (angles[a], angles[b]))


def read_question(html, source):
    try:
        text = re.sub(r"\s+([,.])", r"\1", _text(html, source, labels="ABCDE"))
        ending = "Ответ дайте в градусах."
        if not text.endswith(ending) or text.count("Найдите") != 1:
            raise ContentPlanError("one complete equal-side angle question is required")
        given, request = text[: -len(ending)].strip().split("Найдите")
        prefix = re.match(r"[ВB] треугольнике ABC\s+", given)
        if prefix is None:
            raise ContentPlanError("the complete triangle setup is required")
        rest, angles = given[prefix.end() :], {}
        while match := re.match(r"угол ([ABC]) равен " + _DEGREES, rest):
            if match[1] in angles:
                raise ContentPlanError("a given vertex angle is repeated")
            angles[match[1]] = _value(match[2])
            rest = rest[match.end() :].lstrip(" ,.")
        if rest.startswith("На продолжении"):
            constructor = _extension
        elif re.match(r"[ABC]D [—–-] биссектриса внешнего", rest):
            constructor = _exterior
        else:
            constructor = _congruent
        model = constructor(rest.strip(), request, angles)
        if sum(model.values) >= 180:
            raise ContentPlanError(
                "the given angles must define a nondegenerate triangle"
            )
        return model
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
