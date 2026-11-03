"""Read the altitude/internal-bisector intersection, including opposite line rays."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..isosceles.angle_model import _value
from ..right.altitude_input import _text
from ..right.altitude_solver import AltitudeSolveError
from .altitude_quad_model import _DEGREES


@dataclass(frozen=True)
class HeightBisector:
    theta: sp.Rational
    frame: str

    def name(self, text):
        names = dict(zip("ABC", self.frame)) | {n: n for n in "DHO"}
        return "".join(names[n] for n in text)

    @property
    def answer(self):
        return 90 + self.theta if self.theta < 45 else 90 - self.theta


def read_question(html, source):
    try:
        text = _text(html, source, labels="ABCDHO")
        match = re.fullmatch(
            r"[ВB] треугольнике ABC (?P<c>[ABC])H [—–-] высота, "
            r"(?P<a>[ABC])D [—–-] биссектриса, O [—–-] точка пересечения "
            r"(?P<lines>прямых )?(?P=c)H и (?P=a)D\s*,?\s*угол "
            r"(?P<given>[ABCD]{3}) равен "
            + _DEGREES.replace("(", "(?P<value>", 1)
            + r"\s*\. Найдите угол (?P<target>[ABCO]{3})\s*\. Ответ дайте в градусах\.",
            text,
        )
        if match is None or match["a"] == match["c"]:
            raise ContentPlanError(
                "one complete altitude/bisector intersection is required"
            )
        a, c = match["a"], match["c"]
        b = (set("ABC") - {a, c}).pop()
        if match["given"] not in {
            b + a + "D",
            "D" + a + b,
            c + a + "D",
            "D" + a + c,
        } or match["target"] not in {a + "O" + c, c + "O" + a}:
            raise ContentPlanError(
                "the given bisected angle and requested rays changed"
            )
        theta = _value(match["value"])
        if theta >= 90 or theta == 45:
            raise ContentPlanError("the triangle or requested rays would be degenerate")
        if theta > 45 and not match["lines"]:
            raise ContentPlanError(
                "the external intersection requires explicitly named lines"
            )
        return HeightBisector(theta, a + b + c)
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
