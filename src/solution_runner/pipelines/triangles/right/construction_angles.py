"""Read every statement in the six reviewed two-ray right-triangle families."""

import re
from dataclasses import dataclass
from fractions import Fraction

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...core.numbers import parse_rational
from .altitude_input import _text
from .altitude_solver import AltitudeSolveError

HEIGHT_BISECTOR = "right-triangle-altitude-bisector-angle"
HEIGHT_BISECTOR_INVERSE = "right-triangle-altitude-bisector-inverse"
HEIGHT_MEDIAN = "right-triangle-altitude-line-angle"
HEIGHT_MEDIAN_INVERSE = "right-triangle-altitude-median-inverse"
BISECTOR_MEDIAN = "right-triangle-bisector-median-angle"
BISECTOR_MEDIAN_INVERSE = "right-triangle-bisector-median-inverse"
RULES = {
    HEIGHT_BISECTOR: ("HD", "separation"),
    HEIGHT_BISECTOR_INVERSE: ("HD", "smaller"),
    HEIGHT_MEDIAN: ("HM", "separation"),
    HEIGHT_MEDIAN_INVERSE: ("HM", "larger"),
    BISECTOR_MEDIAN: ("DM", "separation"),
    BISECTOR_MEDIAN_INVERSE: ("DM", "smaller"),
}
SOURCES = {
    "HD": "77e87f28-d563-4212-81ce-0066f8c0f7de",
    "HM": "0f6fdaba-d98a-4e7c-940a-243a8291a549",
    "DM": "b3e2e3c2-c094-41b4-8e6b-2ee9060c77f3",
}
_NUMBER = r"\d+(?:(?:[,.]|\{,\})\d+)?"
_VALUE = r"(?P<value>" + _NUMBER + r")\s*°"
_DEGREES = r" Ответ дайте в градусах\."
_RAYS = {
    "HD": r"высотой(?: CH)? и биссектрисой(?: CD)?",
    "HM": r"высотой(?: CH)? и медианой(?: CM)?",
    "DM": r"биссектрисой(?: CD)? и медианой(?: CM)?",
}
_ORIGIN = r", проведенными из вершины прямого угла(?: C)?"
_GIVENS = (
    (
        "named_b",
        r"Острый угол B прямоугольного треугольника(?: ABC)? равен " + _VALUE + r"\. ",
    ),
    ("acute", r"Один из углов прямоугольного треугольника равен " + _VALUE + r"\. "),
    (
        "acute_pair",
        r"Острые углы прямоугольного треугольника равны "
        + _VALUE
        + r" и (?P<other>"
        + _NUMBER
        + r")\s*°\. ",
    ),
)


@dataclass(frozen=True)
class ConstructionAngles:
    pair: str
    a: Fraction
    b: Fraction
    request: str
    given_kind: str
    givens: tuple[Fraction, ...]

    @property
    def separation(self):
        directions = {"H": self.b, "D": Fraction(45), "M": self.a}
        return abs(directions[self.pair[0]] - directions[self.pair[1]])

    @property
    def answer(self):
        if self.request == "smaller":
            return min(self.a, self.b)
        if self.request == "larger":
            return max(self.a, self.b)
        return self.separation

    @property
    def topology(self):
        return (self.b > 45) - (self.b < 45)

    def require_rule(self, rule):
        expected = RULES.get(rule)
        # The height/median group includes a height/bisector child in the source.
        if expected != (self.pair, self.request) and not (
            rule == HEIGHT_MEDIAN and (self.pair, self.request) == ("HD", "separation")
        ):
            raise ContentPlanError(
                "the complete question differs from the registered construction"
            )
        return self


def _acute(value):
    angle = parse_rational(value)
    if not 0 < angle < 90:
        raise ContentPlanError("both non-right triangle angles must be acute")
    return angle


def read_question(html):
    soup = BeautifulSoup(html, "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one construction figure is required")
    source = images[0].get("data-asset-id", "") if images else ""
    if images:
        if images[0].get("data-asset-key") not in {"image_1", "construction_condition"}:
            raise ContentPlanError("the construction figure key is not reviewed")
        images[0]["data-asset-key"] = "image_1"
    try:
        text = _text(str(soup), source, labels="ABCDHM")
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
    text = text.replace("ё", "е")
    text = re.sub(r"\^\{?\\circ\}?", "°", text)
    text = re.sub(r"\s+([.,])", r"\1", text)
    for given_kind, pattern in _GIVENS:
        match = re.match(pattern, text)
        if match is None:
            continue
        value = _acute(match["value"])
        givens = (value,)
        a, b = 90 - value, value
        if given_kind == "acute_pair":
            other = _acute(match["other"])
            if value + other != 90:
                raise ContentPlanError("the two acute angles must sum to 90 degrees")
            givens = (value, other)
        if given_kind != "named_b":
            a, b = min(value, 90 - value), max(value, 90 - value)
        question = text[match.end() :]
        for pair, rays in _RAYS.items():
            if re.fullmatch(
                r"Найдите (?:угол|величину угла) между "
                + rays
                + _ORIGIN
                + r"\."
                + _DEGREES,
                question,
            ):
                return ConstructionAngles(pair, a, b, "separation", given_kind, givens)
        raise ContentPlanError("the entire two-ray question must be reviewed")
    for pair, rays in _RAYS.items():
        if pair == "DM":
            setup = r"Угол между " + rays + r" прямоугольного треугольника" + _ORIGIN
            request = r"Найдите меньший угол (?:этого|прямоугольного) треугольника\."
            units = r"(?:" + _DEGREES + r")?"
        else:
            setup = r"[ВB] прямоугольном треугольнике угол между " + rays + _ORIGIN
            request = (
                r"Найдите меньший угол данного треугольника\."
                if pair == "HD"
                else r"Найдите больший из острых углов этого треугольника\."
            )
            units = _DEGREES
        match = re.fullmatch(
            setup + r", равен " + _VALUE + r"\. " + request + units, text
        )
        if match is None:
            continue
        phi = parse_rational(match["value"])
        bound = 90 if pair == "HM" else 45
        if not 0 <= phi < bound:
            raise ContentPlanError(
                "the ray separation cannot define a nondegenerate right triangle"
            )
        a = (90 - phi) / 2 if pair == "HM" else 45 - phi
        return ConstructionAngles(
            pair,
            a,
            90 - a,
            "larger" if pair == "HM" else "smaller",
            "separation",
            (phi,),
        )
    raise ContentPlanError(
        "every construction statement, value, request and unit is required"
    )


def read_context(context):
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise ContentPlanError("schema-v3 normalized construction content is required")
    conditions = [s for s in content.get("sections", []) if s.get("key") == "condition"]
    if len(conditions) != 1 or not isinstance(conditions[0].get("html"), str):
        raise ContentPlanError("one complete construction condition is required")
    return read_question(conditions[0]["html"])
