"""Read a complete two-side/two-height question and derive its geometry exactly."""

import re
from dataclasses import dataclass

import sympy as sp

from ...core.errors import ContentPlanError
from ..right.altitude_input import _text
from ..right.altitude_solver import AltitudeSolveError, _parse_positive_value


@dataclass(frozen=True)
class HeightArea:
    a: sp.Expr
    b: sp.Expr
    h: sp.Expr

    @property
    def answer(self):
        return sp.simplify(self.a * self.h / self.b)

    @property
    def native_compatible(self):
        p = self.points
        v = p["C"] - p["B"]
        parameters = (
            sp.simplify(p["H"].dot(p["B"]) / p["B"].dot(p["B"])),
            sp.simplify((p["K"] - p["B"]).dot(v) / v.dot(v)),
        )
        return all(
            t.is_positive is True and (1 - t).is_positive is True for t in parameters
        )

    @property
    def points(self):
        x = sp.simplify(self.a - sp.sqrt(self.b**2 - self.h**2))
        c = sp.sqrt(x * x + self.h * self.h)
        bx = sp.simplify((self.a * self.a + c * c - self.b * self.b) / (2 * c))
        by = -sp.simplify(self.a * self.h / c)
        a, b, cpoint = sp.Matrix([0, 0]), sp.Matrix([bx, by]), sp.Matrix([c, 0])
        hpoint = sp.simplify(cpoint.dot(b) / b.dot(b)) * b
        delta = cpoint - b
        k = sp.simplify((-b).dot(delta) / delta.dot(delta))
        return {
            "A": a,
            "B": b,
            "C": cpoint,
            "H": hpoint,
            "K": sp.simplify(b + k * delta),
        }


def read_question(html, source):
    try:
        text = _text(html, source, labels="ABCHK")
        match = re.fullmatch(
            r"У треугольника со сторонами (.+?) и (.+?) проведены высоты к этим сторонам\. "
            r"Высота, проведенная к первой стороне, равна (.+?)\. "
            r"Чему равна высота, проведенная ко второй стороне\?",
            text,
        )
        if match is None:
            raise ContentPlanError(
                "the complete two-side/two-height question is required"
            )
        a, b, h = map(_parse_positive_value, match.groups())
        if sp.simplify(h - b).is_positive:
            raise ContentPlanError(
                "the height to the first side cannot exceed the second side"
            )
        if (b - h).is_nonnegative is not True:
            raise ContentPlanError(
                "the given height must define a real nondegenerate triangle"
            )
        return HeightArea(a, b, h)
    except AltitudeSolveError as exc:
        raise ContentPlanError(str(exc)) from exc
