"""Read inverse pairs of side/base questions with an exact included angle."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..right.altitude_input import _text, _value
from ..right.altitude_solver import AltitudeSolveError, _parse_positive_value
from .side_altitude_model import _setup

RULES = {
    "isosceles-triangle-27799-side-from-base-vertex-angle": ("base", "side"),
    "isosceles-triangle-27800-base-from-side-vertex-angle": ("side", "base"),
}
_SEGMENT = r"(?:AB|BA|AC|CA|BC|CB)"
_DEGREE = r"(\d+(?:(?:[.,]|\{,\})\d+)?)(?:°|\^\{\\circ\}|\^\\circ)(?=\s|[,.;]|$)"


@dataclass(frozen=True)
class CosineTriangle:
    apex: str
    given_kind: str
    length_raw: str
    apex_angle: sp.Rational
    requested_kind: str
    requested: str

    @property
    def base_vertices(self):
        return tuple(sorted(set("ABC") - {self.apex}))

    @property
    def base_segment(self):
        return "".join(self.base_vertices)

    @property
    def equal_sides(self):
        return tuple("".join(sorted((v, self.apex))) for v in self.base_vertices)

    @property
    def cosine(self):
        return sp.simplify(sp.cos(sp.pi * self.apex_angle / 180))

    @property
    def factor(self):
        return sp.simplify(2 * (1 - self.cosine))

    @property
    def side(self):
        value = _parse_positive_value(self.length_raw)
        return (
            value
            if self.given_kind == "side"
            else sp.simplify(value / sp.sqrt(self.factor))
        )

    @property
    def base(self):
        value = _parse_positive_value(self.length_raw)
        return (
            value
            if self.given_kind == "base"
            else sp.simplify(value * sp.sqrt(self.factor))
        )

    @property
    def answer(self):
        return self.side if self.requested_kind == "side" else self.base

    @property
    def topology(self):
        return 0 if self.apex_angle == 90 else 1 if self.apex_angle < 90 else -1

    def require_rule(self, rule):
        if RULES.get(rule) != (self.given_kind, self.requested_kind):
            raise ContentPlanError(
                "the complete cosine question differs from its registered rule"
            )
        return self


def _facts(rest, side):
    lengths = {} if side is None else {"side": side}
    angle = None
    while rest.strip(" ,."):
        rest = rest.lstrip(" ,.")
        assignment = re.match(r"(" + _SEGMENT + r")\s*=\s*", rest)
        degree = re.match(r"угол ([ABC]) равен " + _DEGREE, rest)
        if degree and angle is None:
            angle = (
                degree[1],
                sp.Rational(degree[2].replace("{,}", ".").replace(",", ".")),
            )
            rest = rest[degree.end() :]
        elif assignment:
            key = "".join(sorted(assignment[1]))
            if key in lengths:
                raise ContentPlanError("duplicate included-angle length givens")
            raw, rest = _value(rest[assignment.end() :])
            lengths[key] = raw
        else:
            raise ContentPlanError(
                "an unreviewed or repeated included-angle statement remains"
            )
    return lengths, angle


def read_question(html, source):
    try:
        text = _text(html, source)
        if text.count("Найдите") != 1:
            raise ContentPlanError("one complete cosine question is required")
        given, request = text.split("Найдите")
        apex, side, rest = _setup(given)
        lengths, angle = _facts(rest, side)
        target = re.fullmatch(r"\s*(" + _SEGMENT + r")\s*\.\s*", request)
        if (
            target is None
            or angle is None
            or angle[0] != apex
            or not 0 < angle[1] < 180
        ):
            raise ContentPlanError(
                "the complete question must specify an included vertex angle and one new side"
            )
        p, q = sorted(set("ABC") - {apex})
        base = p + q
        sides = {"".join(sorted((v, apex))) for v in (p, q)}
        if len(lengths) != 1:
            raise ContentPlanError("exactly one independent length must be given")
        key, raw = next(iter(lengths.items()))
        kind = (
            "side" if key == "side" or key in sides else "base" if key == base else None
        )
        requested = "".join(sorted(target[1]))
        wanted = "base" if requested == base else "side"
        if kind is None or kind == wanted:
            raise ContentPlanError(
                "the requested length must be the opposite side/base quantity"
            )
        model = CosineTriangle(apex, kind, raw, angle[1], wanted, requested)
        if model.cosine.has(sp.cos):
            raise ContentPlanError("an exact reviewed cosine value is required")
        return model
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
