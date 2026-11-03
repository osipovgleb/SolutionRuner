"""Read complete base/side questions and solve their shared half-triangle exactly."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..right.altitude_input import _text, _value
from ..right.altitude_solver import AltitudeSolveError, _parse_positive_value

RULES = {
    "isosceles-triangle-27284-base-from-sine": ("sin", "side"),
    "isosceles-triangle-27285-side-from-base-sine": ("sin", "base"),
    "isosceles-triangle-27286-base-from-cosine": ("cos", "side"),
    "isosceles-triangle-27287-side-from-base-cosine": ("cos", "base"),
    "isosceles-triangle-27288-base-from-tangent": ("tg", "side"),
    "isosceles-triangle-27289-side-from-base-tangent": ("tg", "base"),
}


@dataclass(frozen=True)
class BasicTriangle:
    given_kind: str
    given_length: sp.Expr
    length_latex: str
    function: str
    angle: str
    function_value: sp.Expr
    function_latex: str
    requested: str

    @property
    def cosine(self):
        t = self.function_value
        if self.function == "sin":
            return sp.simplify(sp.sqrt(1 - t * t))
        if self.function == "cos":
            return t
        return sp.simplify(1 / sp.sqrt(1 + t * t))

    @property
    def side(self):
        return (
            self.given_length
            if self.given_kind == "side"
            else sp.simplify(self.given_length / (2 * self.cosine))
        )

    @property
    def base(self):
        return (
            self.given_length
            if self.given_kind == "base"
            else sp.simplify(2 * self.given_length * self.cosine)
        )

    @property
    def answer(self):
        return self.base if self.requested == "AB" else self.side

    def require_rule(self, rule):
        if RULES.get(rule) != (self.function, self.given_kind):
            raise ContentPlanError(
                "the complete isosceles question differs from the registered rule"
            )
        return self


def read_question(html, source):
    try:
        text = _text(html, source)
        setup = re.match(r"[ВB] треугольнике ABC\s+AC\s*=\s*BC\s*", text)
        if setup is None:
            raise ContentPlanError("the complete question must explicitly state AC=BC")
        rest = text[setup.end() :]
        if rest.startswith("="):
            kind, rest = "side", rest[1:]
        else:
            base = re.match(r",\s*AB\s*=\s*", rest)
            if base is None:
                raise ContentPlanError(
                    "one complete equal-side or base length is required"
                )
            kind, rest = "base", rest[base.end() :]
        raw_length, rest = _value(rest)
        trig = re.match(r"\s*,\s*\\(sin|cos|tg)\s*([AB])\s*=\s*", rest)
        if trig is None:
            raise ContentPlanError("one base-angle trigonometric value is required")
        raw_trig, rest = _value(rest[trig.end() :])
        request = re.fullmatch(r"\s*\.\s*Найдите\s+(AB|AC|BC)\s*\.\s*", rest)
        if request is None or (kind == "side") != (request[1] == "AB"):
            raise ContentPlanError("the whole request must determine a new side")
        value = _parse_positive_value(raw_trig)
        if trig[1] in {"sin", "cos"} and (1 - value).is_positive is not True:
            raise ContentPlanError(
                "a nondegenerate isosceles base angle has sine and cosine between zero and one"
            )
        return BasicTriangle(
            kind,
            _parse_positive_value(raw_length),
            raw_length,
            trig[1],
            trig[2],
            value,
            raw_trig,
            request[1],
        )
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc


def read_context(context):
    from bs4 import BeautifulSoup

    from .planner import _section

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise ContentPlanError("schema-v3 normalized isosceles content is required")
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError("a complete isosceles condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one isosceles condition figure is required")
    source = images[0].get("data-asset-id", "") if images else ""
    if images and images[0].get("data-asset-key") == "isosceles_condition":
        images[0]["data-asset-key"] = "image_1"
    return read_question(str(soup), source)
