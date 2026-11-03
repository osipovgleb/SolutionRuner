"""Read isosceles side-altitude families while preserving the actual vertex names."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..right.altitude_input import _text, _value
from ..right.altitude_solver import AltitudeSolveError, _parse_positive_value
from .basic_model import BasicTriangle

RULES = {
    "isosceles-triangle-27320-altitude-from-base-sine": ("base", "sin", "height"),
    "isosceles-triangle-27321-projection-from-base-sine": ("base", "sin", "projection"),
    "isosceles-triangle-27322-altitude-from-base-cosine": ("base", "cos", "height"),
    "isosceles-triangle-27323-projection-from-base-cosine": (
        "base",
        "cos",
        "projection",
    ),
    "isosceles-triangle-27324-altitude-from-base-tangent": ("base", "tg", "height"),
    "isosceles-triangle-27325-projection-from-base-tangent": (
        "base",
        "tg",
        "projection",
    ),
    "isosceles-triangle-27326-altitude-from-side-sine": ("side", "sin", "height"),
    "isosceles-triangle-27327-projection-from-side-sine": ("side", "sin", "projection"),
    "isosceles-triangle-27328-altitude-from-side-cosine": ("side", "cos", "height"),
    "isosceles-triangle-27329-projection-from-side-cosine": (
        "side",
        "cos",
        "projection",
    ),
    "isosceles-triangle-27330-sine-from-altitude-and-base": (
        "base_height",
        None,
        "sin",
    ),
    "isosceles-triangle-27331-cosine-from-altitude-and-base": (
        "base_height",
        None,
        "cos",
    ),
}
_SEGMENT = r"(?:AB|BA|AC|CA|BC|CB)"


@dataclass(frozen=True)
class SideAltitudeTriangle:
    triangle: BasicTriangle
    vertex: str
    other_base_vertex: str
    apex: str
    given_kind: str
    requested_kind: str
    requested: str
    given_angle: str
    given_height: tuple[sp.Expr, str] | None = None

    @property
    def height_segment(self):
        return self.vertex + "H"

    @property
    def projection_segment(self):
        return self.other_base_vertex + "H"

    @property
    def base_segment(self):
        return "".join(sorted((self.vertex, self.other_base_vertex)))

    @property
    def side_segment(self):
        return "".join(sorted((self.vertex, self.apex)))

    @property
    def height(self):
        return sp.simplify(self.triangle.base * self.triangle.sine)

    @property
    def projection(self):
        return sp.simplify(self.triangle.base * self.triangle.cosine)

    @property
    def topology(self):
        difference = sp.simplify(2 * self.triangle.cosine**2 - 1)
        if difference == 0:
            return 0
        if difference.is_positive is True:
            return 1
        if difference.is_negative is True:
            return -1
        raise ContentPlanError("the side-altitude topology must be determined exactly")

    @property
    def answer(self):
        return {
            "height": self.height,
            "projection": self.projection,
            "sin": self.triangle.sine,
            "cos": self.triangle.cosine,
        }[self.requested_kind]

    def require_rule(self, rule):
        function = None if self.given_kind == "base_height" else self.triangle.function
        if RULES.get(rule) != (self.given_kind, function, self.requested_kind):
            raise ContentPlanError(
                "the full side-altitude question differs from the registered rule"
            )
        return self


def _setup(text):
    setup = re.match(
        r"[ВB] треугольнике ABC\s+(" + _SEGMENT + r")\s*=\s*(" + _SEGMENT + r")\s*",
        text,
    )
    if setup:
        first, second = setup[1], setup[2]
        common = set(first) & set(second)
        if len(common) != 1 or set(first + second) != set("ABC"):
            raise ContentPlanError("two distinct equal sides of ABC must be given")
        apex = common.pop()
        rest = text[setup.end() :]
        side = None
        if rest.startswith("="):
            side, rest = _value(rest[1:])
        return apex, side, rest
    setup = re.match(
        r"[ВB] равнобедренном треугольнике ABC с основанием ("
        + _SEGMENT
        + r") боковая сторона равна\s*",
        text,
    )
    if setup is None:
        raise ContentPlanError(
            "the complete isosceles setup must specify its equal sides or base"
        )
    side, rest = _value(text[setup.end() :])
    return (set("ABC") - set(setup[1])).pop(), side, rest


def _facts(rest, side):
    lengths = {} if side is None else {"side": (_parse_positive_value(side), side)}
    trig = None
    height = None
    while rest.strip(" ,."):
        rest = rest.lstrip(" ,.")
        definition = re.match(r"([ABC]H)\s*[—–−-]\s*высота\b", rest)
        assigned_height = re.match(r"высота ([ABC]H) равна\s*", rest)
        if definition or assigned_height:
            match = definition or assigned_height
            if height is not None:
                raise ContentPlanError("the side altitude must be defined once")
            height = match[1]
            rest = rest[match.end() :]
            if assigned_height:
                raw, rest = _value(rest)
                lengths[height] = (_parse_positive_value(raw), raw)
            continue
        assignment = re.match(r"(" + _SEGMENT + r")\s*=\s*", rest)
        function = re.match(
            r"\\(sin|cos|tg)\s*(?:\\angle\s*)?([ABC]{1,3})\s*=\s*", rest
        )
        if assignment:
            key = "".join(sorted(assignment[1]))
            if key in lengths:
                raise ContentPlanError("duplicate side-altitude length givens")
            raw, rest = _value(rest[assignment.end() :])
            lengths[key] = (_parse_positive_value(raw), raw)
        elif function and trig is None:
            raw, rest = _value(rest[function.end() :])
            trig = (function[1], function[2], _parse_positive_value(raw), raw)
        else:
            raise ContentPlanError("an unreviewed side-altitude statement remains")
    return lengths, trig, height


def _request(text):
    height = re.fullmatch(r"(?:высоту|длину высоты)\s+([ABC]H)\s*\.?", text)
    if height:
        return "height", height[1]
    projection = re.fullmatch(r"([ABC]H)\s*\.?", text)
    if projection:
        return "projection", projection[1]
    function = re.fullmatch(
        r"(?:синус угла\s+([ABC]{1,3})|косинус угла\s+([ABC]{1,3})|\\(sin|cos)\s*(?:\\angle\s*)?([ABC]{1,3}))\s*\.?",
        text,
    )
    if function:
        kind = "sin" if function[1] else "cos" if function[2] else function[3]
        return kind, function[1] or function[2] or function[4]
    raise ContentPlanError("the entire side-altitude request must be reviewed")


def _angle(angle, vertices):
    if (len(angle) == 1 and angle in vertices) or (
        len(angle) == 3 and set(angle) == set("ABC") and angle[1] in vertices
    ):
        return
    raise ContentPlanError("the trigonometric angle must be one of the two base angles")


def _triangle(lengths, trig, base, sides, height, angle):
    if trig:
        if len(lengths) != 1:
            raise ContentPlanError(
                "one length and one trigonometric value are required"
            )
        key, (length, raw) = next(iter(lengths.items()))
        kind = (
            "side" if key == "side" or key in sides else "base" if key == base else None
        )
        if kind is None:
            raise ContentPlanError("the given length must be the base or an equal side")
        function, angle, value, trig_raw = trig
        if function in {"sin", "cos"} and (1 - value).is_positive is not True:
            raise ContentPlanError("the isosceles base angle must be acute")
        return (
            BasicTriangle(kind, length, raw, function, angle, value, trig_raw, "AB"),
            kind,
            None,
        )
    if set(lengths) != {base, height}:
        raise ContentPlanError(
            "the inverse question needs exactly the base and side-altitude lengths"
        )
    (b, raw_b), (h, raw_h) = lengths[base], lengths[height]
    ratio = sp.simplify(h / b)
    if (1 - ratio).is_positive is not True:
        raise ContentPlanError("the side altitude must be shorter than the base")
    return (
        BasicTriangle(
            "base",
            b,
            raw_b,
            "sin",
            angle,
            ratio,
            r"\frac{" + raw_h + "}{" + raw_b + "}",
            "AB",
        ),
        "base_height",
        (h, raw_h),
    )


def read_question(html, source):
    try:
        text = _text(html, source)
        if text.count("Найдите") != 1:
            raise ContentPlanError("one complete side-altitude question is required")
        given, request = text.split("Найдите")
        apex, side, rest = _setup(given)
        lengths, trig, height = _facts(rest, side)
        kind, target = _request(request.strip())
        if kind == "height":
            if height is not None and height != target:
                raise ContentPlanError(
                    "the defined altitude differs from the requested altitude"
                )
            height = target
        if height is None:
            raise ContentPlanError("the side altitude must be explicitly defined")
        vertex = height[0]
        base_vertices = set("ABC") - {apex}
        if vertex not in base_vertices:
            raise ContentPlanError("the altitude must start at a base vertex")
        other = (base_vertices - {vertex}).pop()
        if kind == "projection" and target != other + "H":
            raise ContentPlanError(
                "the requested projection must start at the other base vertex"
            )
        angle = trig[1] if trig else target
        _angle(angle, base_vertices)
        if kind in {"sin", "cos"}:
            _angle(target, base_vertices)
        base = "".join(sorted(base_vertices))
        sides = {"".join(sorted((v, apex))) for v in base_vertices}
        triangle, given_kind, given_height = _triangle(
            lengths, trig, base, sides, height, angle
        )
        if (given_kind == "base_height") != (kind in {"sin", "cos"}):
            raise ContentPlanError(
                "the request must determine a new side-altitude quantity"
            )
        return SideAltitudeTriangle(
            triangle, vertex, other, apex, given_kind, kind, target, angle, given_height
        )
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc


def read_context(context):
    from bs4 import BeautifulSoup

    from .planner import _section
    from .side_altitude_sources import generated_keys

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise ContentPlanError("schema-v3 normalized side-altitude content is required")
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError("a complete side-altitude condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one side-altitude condition image is required")
    source = images[0].get("data-asset-id", "") if images else ""
    if images and images[0].get("data-asset-key") in generated_keys():
        images[0]["data-asset-key"] = "image_1"
    return read_question(str(soup), source)
