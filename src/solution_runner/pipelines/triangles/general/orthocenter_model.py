"""Read the three altitude roles and preserve the actual rays of angle AOF."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..isosceles.angle_model import _value
from ..right.altitude_input import _text
from ..right.altitude_solver import AltitudeSolveError
from .altitude_quad_model import _DEGREES
from .incenter_model import _RAY


@dataclass(frozen=True)
class OrthocenterAngle:
    frame: str
    alpha: sp.Rational
    beta: sp.Rational

    def name(self, text):
        names = dict(zip("ABC", self.frame)) | {n: n for n in "DEFO"}
        return "".join(names[n] for n in text)

    @property
    def gamma(self):
        return 180 - self.alpha - self.beta

    @property
    def answer(self):
        return min(self.beta, 180 - self.beta)


def _facts(text):
    angles, heights = {}, None
    while text.strip(" ,."):
        text = text.lstrip(" ,.")
        angle = re.match(r"угол ([ABC]) равен " + _DEGREES, text)
        construction = re.match(
            _RAY
            + r", "
            + _RAY
            + " и "
            + _RAY
            + r" [—–-] высоты, пересекающиеся в точке O\b",
            text,
        )
        if angle and angle[1] not in angles:
            angles[angle[1]] = _value(angle[2])
            end = angle.end()
        elif construction and heights is None:
            segments = construction.groups()
            heights = {
                next(n for n in s if n in "DEF"): next(n for n in s if n in "ABC")
                for s in segments
            }
            if set(heights) != set("DEF") or set(heights.values()) != set("ABC"):
                raise ContentPlanError(
                    "three distinct altitude origins and feet are required"
                )
            end = construction.end()
        else:
            raise ContentPlanError("an unreviewed or repeated orthocenter fact remains")
        text = text[end:]
    return angles, heights


def read_question(html, source):
    try:
        text = _text(html, source, labels="ABCDEFO")
        text = re.sub(r"\s+([,.])", r"\1", text)
        end = "Ответ дайте в градусах."
        if not text.endswith(end) or text.count("Найдите") != 1:
            raise ContentPlanError(
                "one complete orthocenter angle question is required"
            )
        given, request = text[: -len(end)].strip().split("Найдите")
        prefix = re.match(r"[ВB] треугольнике ABC\s+", given)
        target = re.fullmatch(r"\s*угол ([ABCDEFO]{3})\.\s*", request)
        if prefix is None or target is None:
            raise ContentPlanError(
                "the complete triangle and requested angle are required"
            )
        angles, heights = _facts(given[prefix.end() :])
        if heights is None:
            raise ContentPlanError("three altitudes through O are required")
        a, b, c = (heights[n] for n in "DEF")
        if set(angles) != {a, b} or target[1] not in {a + "OF", "FO" + a}:
            raise ContentPlanError(
                "the given vertex angles or requested altitude rays changed"
            )
        model = OrthocenterAngle(a + b + c, angles[a], angles[b])
        if model.gamma <= 0 or model.alpha == 90 or model.beta == 90:
            raise ContentPlanError(
                "the triangle or the rays of angle AOF would be degenerate"
            )
        return model
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
