"""Read a complete height-angle subtraction with the reviewed external foot H."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..isosceles.angle_model import _value
from ..right.altitude_input import _text
from ..right.altitude_solver import AltitudeSolveError
from .altitude_quad_model import _DEGREES


@dataclass(frozen=True)
class HeightSubtraction:
    frame: str
    alpha: sp.Rational
    delta: sp.Rational

    def name(self, text):
        names = dict(zip("ABC", self.frame)) | {"H": "H"}
        return "".join(names[n] for n in text)

    @property
    def intermediate(self):
        return 90 - self.alpha

    @property
    def answer(self):
        return self.intermediate - self.delta


def read_question(html, source):
    try:
        text = _text(html, source, labels="ABCH")
        text = re.sub(r"\s+([,.])", r"\1", text)
        match = re.fullmatch(
            r"[ВB] треугольнике ABC угол (?P<a>[ABC]) равен "
            + _DEGREES.replace("(", "(?P<alpha>", 1)
            + r", (?:угол (?P<b>[ABC]) [—–-] тупой, )?"
            r"(?P<c>[ABC])H [—–-] высота, угол (?P<given>[ABCH]{3}) равен "
            + _DEGREES.replace("(", "(?P<delta>", 1)
            + r"\. Найдите угол (?P<target>[ABC]{3})\. Ответ дайте в градусах\.",
            text,
        )
        if match is None or match["a"] == match["c"]:
            raise ContentPlanError(
                "one complete reviewed height-angle question is required"
            )
        a, c = match["a"], match["c"]
        b = (set("ABC") - {a, c}).pop()
        if (
            (match["b"] is not None and match["b"] != b)
            or match["given"] not in {b + c + "H", "H" + c + b}
            or match["target"] not in {a + c + b, b + c + a}
        ):
            raise ContentPlanError("the external-foot premise or angle rays changed")
        alpha, delta = _value(match["alpha"]), _value(match["delta"])
        if alpha + delta >= 90:
            raise ContentPlanError(
                "the reviewed external-foot triangle would be degenerate"
            )
        return HeightSubtraction(a + b + c, alpha, delta)
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
