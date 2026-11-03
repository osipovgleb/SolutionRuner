"""Read complete two-altitude quadrilateral questions and their acute-angle premises."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..isosceles.angle_model import _value
from ..right.altitude_input import _text
from ..right.altitude_solver import AltitudeSolveError
from .incenter_model import _RAY

ALL_ACUTE = "general-triangle-27762-orthocenter-angle"
OTHER_ACUTE = "general-triangle-500142-altitudes-obtuse-angle"
_DEGREES = r"(\d+(?:(?:[.,]|\{,\})\d+)?)\s*(?:°|\^\{\\circ\}|градус(?:ам|а|ов)?)"
_END = "Ответ дайте в градусах."


@dataclass(frozen=True)
class AltitudeQuad:
    alpha: sp.Rational
    frame: str
    all_acute: bool

    def name(self, name):
        mapping = dict(zip("ABC", self.frame)) | {n: n for n in "DEO"}
        return "".join(mapping[n] for n in name)

    @property
    def answer(self):
        return 180 - self.alpha

    def require_rule(self, rule):
        if rule not in {ALL_ACUTE, OTHER_ACUTE} or (
            rule == ALL_ACUTE and not self.all_acute
        ):
            raise ContentPlanError(
                "the complete altitude premise differs from the registered rule"
            )
        return self


def _facts(text):
    given = None
    acute = None
    rays = None
    extended = False
    while text.strip(" ,."):
        text = text.lstrip(" ,.")
        angle = re.match(r"угол ([ABC]) равен " + _DEGREES, text)
        declared = re.match(r"(?:а )?углы ([ABC]) и ([ABC]) [—–-] острые\b", text)
        before = re.match(
            r"(высоты|продолжения высот) "
            + _RAY
            + " и "
            + _RAY
            + r" пересекаются в точке O\b",
            text,
        )
        construction = before or re.match(
            _RAY + " и " + _RAY + r" [—–-] высоты, пересекающиеся в точке O\b", text
        )
        if angle and given is None:
            given = (angle[1], _value(angle[2]))
            end = angle.end()
        elif declared and acute is None:
            acute = {declared[1], declared[2]}
            end = declared.end()
            if len(acute) != 2:
                raise ContentPlanError(
                    "two distinct acute vertex angles must be specified"
                )
        elif construction and rays is None:
            segments = construction.groups()[1:] if before else construction.groups()
            extended = bool(before and before[1] == "продолжения высот")
            rays = {
                next(n for n in s if n in "DEF"): next(n for n in s if n in "ABC")
                for s in segments
            }
            if set(rays) != {"D", "E"} or len(set(rays.values())) != 2:
                raise ContentPlanError(
                    "two distinct altitude origins and feet D and E are required"
                )
            end = construction.end()
        else:
            raise ContentPlanError("an unreviewed or repeated altitude fact remains")
        text = text[end:]
    if given is None or rays is None:
        raise ContentPlanError(
            "one vertex angle and two intersecting altitudes are required"
        )
    return given, acute, rays, extended


def read_question(html, source):
    try:
        text = _text(html, source, labels="ABCDEO")
        if not text.endswith(_END) or text.count("Найдите") != 1:
            raise ContentPlanError(
                "one complete altitude-angle question with degree units is required"
            )
        given, request = text[: -len(_END)].strip().split("Найдите")
        prefix = re.match(r"[ВB] (остроугольном )?треугольнике ABC\s+", given)
        target = re.fullmatch(r"\s*угол (DOE|EOD)\s*\.\s*", request)
        if prefix is None or target is None:
            raise ContentPlanError(
                "the complete triangle setup and angle DOE are required"
            )
        (vertex, alpha), acute, rays, extended = _facts(given[prefix.end() :])
        other = {rays["D"], rays["E"]}
        a = (set("ABC") - other).pop()
        all_acute = prefix[1] is not None
        if (
            vertex != a
            or (acute is not None and acute != other)
            or (not all_acute and acute != other)
        ):
            raise ContentPlanError(
                "the two remaining vertex angles must be explicitly acute"
            )
        if (all_acute and alpha >= 90) or alpha == 90:
            raise ContentPlanError(
                "the acute premise or the distinct rays of angle DOE would fail"
            )
        if extended != (alpha > 90):
            raise ContentPlanError(
                "external orthocenter rays require explicitly extended altitudes"
            )
        return AltitudeQuad(alpha, a + rays["D"] + rays["E"], bool(alpha < 90))
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
