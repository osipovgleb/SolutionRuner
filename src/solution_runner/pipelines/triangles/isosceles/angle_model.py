"""Read complete isosceles angle questions and reject ambiguous triangles."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..right.altitude_input import _text
from ..right.altitude_solver import AltitudeSolveError

RULES = {
    "isosceles-triangle-27744-vertex-angle-from-base-angle": ("base", "vertex"),
    "isosceles-triangle-27745-base-angle-from-vertex-angle": ("vertex", "base"),
    "isosceles-triangle-27746-exterior-angle-from-vertex-angle": (
        "vertex",
        "external_base",
    ),
    "isosceles-triangle-27747-vertex-angle-from-exterior-base-angle": (
        "external_base",
        "vertex",
    ),
    "isosceles-triangle-27748-base-angle-from-exterior-vertex-angle": (
        "external_vertex",
        "base",
    ),
    "isosceles-triangle-27750-smaller-angle-from-larger-angle": ("larger", "smaller"),
    "isosceles-triangle-27754-smaller-angle-from-angle-difference": (
        "difference",
        "smaller",
    ),
}
_SEGMENT = r"(?:AB|BA|AC|CA|BC|CB)"
_DEGREES = r"(\d+(?:(?:[.,]|\{,\})\d+)?)(?:°|\^\{\\circ\})"
_END = "Ответ дайте в градусах."


@dataclass(frozen=True)
class AngleTriangle:
    apex: str
    given_kind: str
    given_vertex: str
    given_value: sp.Rational
    requested_kind: str
    requested: str
    apex_angle: sp.Rational

    @property
    def base_vertices(self):
        return tuple(sorted(set("ABC") - {self.apex}))

    @property
    def base_angle(self):
        return (180 - self.apex_angle) / 2

    @property
    def answer(self):
        return {
            "vertex": self.apex_angle,
            "base": self.base_angle,
            "external_base": 180 - self.base_angle,
            "smaller": self.base_angle,
        }[self.requested_kind]

    @property
    def topology(self):
        return 0 if self.apex_angle == 90 else 1 if self.apex_angle < 90 else -1

    def require_rule(self, rule):
        if RULES.get(rule) != (self.given_kind, self.requested_kind):
            raise ContentPlanError(
                "the complete angle question differs from its registered rule"
            )
        return self


def _value(raw):
    value = sp.Rational(raw.replace("{,}", ".").replace(",", "."))
    if not 0 < value < 180:
        raise ContentPlanError(
            "the given angle or difference must lie strictly between zero and 180 degrees"
        )
    return value


def _model(apex, kind, vertex, value, target, requested):
    if kind == "larger" and value <= 60:
        raise ContentPlanError("a distinct larger angle must exceed 60 degrees")
    if kind in {"larger", "difference"} and value < 90:
        raise ContentPlanError(
            "the angle statement admits two distinct isosceles triangles"
        )
    apex_angle = {
        "base": 180 - 2 * value,
        "vertex": value,
        "external_base": 2 * value - 180,
        "external_vertex": 180 - value,
        "larger": value,
        "difference": (180 + 2 * value) / 3,
    }[kind]
    if not 0 < apex_angle < 180:
        raise ContentPlanError(
            "the angles must form a nondegenerate isosceles triangle"
        )
    return AngleTriangle(apex, kind, vertex, value, target, requested, apex_angle)


def _facts(text):
    equal = None
    given = None
    declaration = None
    while text.strip(" ,."):
        text = text.lstrip(" ,.")
        sides = re.match(
            r"("
            + _SEGMENT
            + r")\s*=\s*("
            + _SEGMENT
            + r")\b|стороны ("
            + _SEGMENT
            + r") и ("
            + _SEGMENT
            + r") равны\b",
            text,
        )
        angle = re.match(r"угол ([ABC]) равен " + _DEGREES, text)
        external = re.match(r"Внешний угол при вершине ([ABC]) равен " + _DEGREES, text)
        stated = re.match(r"угол ([ABC][ABC]D) [—–-] внешний\b", text)
        if sides and equal is None:
            equal = (sides[1] or sides[3], sides[2] or sides[4])
            end = sides.end()
        elif (angle or external) and given is None:
            match = angle or external
            given = (bool(external), match[1], _value(match[2]))
            end = match.end()
        elif stated and declaration is None:
            declaration = stated[1]
            end = stated.end()
        else:
            raise ContentPlanError("an unreviewed or repeated angle statement remains")
        text = text[end:]
    if equal is None or given is None:
        raise ContentPlanError(
            "one equal-side relation and one angle must be specified"
        )
    common = set(equal[0]) & set(equal[1])
    if len(common) != 1 or set("".join(equal)) != set("ABC"):
        raise ContentPlanError("two distinct equal sides must define the apex")
    return common.pop(), given, declaration


def _named(given, request):
    prefix = re.match(r"[ВB] треугольнике ABC\s+", given)
    if prefix is None:
        raise ContentPlanError("the complete named triangle setup is required")
    apex, (external, vertex, value), declaration = _facts(given[prefix.end() :])
    kind = ("external_" if external else "") + ("vertex" if vertex == apex else "base")
    target = re.fullmatch(r"\s*(внешний )?угол ([ABC]|[ABC][ABC]D)\s*\.\s*", request)
    if target is None:
        raise ContentPlanError(
            "one complete internal or exterior angle request is required"
        )
    requested = target[2]
    if target[1]:
        if (
            len(requested) != 3
            or requested[0] != apex
            or requested[1] == apex
            or requested[0] == requested[1]
        ):
            raise ContentPlanError(
                "the exterior base angle must extend the base at its endpoint"
            )
        wanted = "external_base"
    else:
        if len(requested) != 1:
            raise ContentPlanError("the requested internal angle must name one vertex")
        wanted = "vertex" if requested == apex else "base"
    if declaration is not None and (not target[1] or declaration != requested):
        raise ContentPlanError("the declared exterior angle differs from the request")
    return _model(apex, kind, vertex, value, wanted, requested)


def read_question(html, source):
    try:
        text = _text(html, source, labels="ABCD")
        if not text.endswith(_END) or text.count("Найдите") != 1:
            raise ContentPlanError(
                "one complete angle question with degree units is required"
            )
        given, request = text[: -len(_END)].strip().split("Найдите")
        if given.startswith(("В треугольнике", "B треугольнике")):
            return _named(given, request)
        larger = re.fullmatch(
            r"Больший угол равнобедренного треугольника равен "
            + _DEGREES
            + r"\s*\.\s*",
            given,
        )
        difference = re.fullmatch(
            r"Один угол равнобедренного треугольника на "
            + _DEGREES
            + r" больше другого\.\s*",
            given,
        )
        if not (larger or difference) or not re.fullmatch(
            r"\s*меньший угол\.\s*", request
        ):
            raise ContentPlanError(
                "the complete unnamed angle comparison must be reviewed"
            )
        match = larger or difference
        return _model(
            "C",
            "larger" if larger else "difference",
            "C",
            _value(match[1]),
            "smaller",
            "A",
        )
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
