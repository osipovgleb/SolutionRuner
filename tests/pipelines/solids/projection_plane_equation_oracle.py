"""Verify every displayed equation against an independently constructed solid."""

import re

import sympy as sp
from altitude_geometry_oracle import substitute
from bs4 import BeautifulSoup
from projection_plane_geometry import geometry

from solution_runner.pipelines.equations.logarithm_parser import Node
from solution_runner.pipelines.equations.power_arithmetic import balanced
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser


def values_for(points, extra):
    values = {
        a + b: sp.simplify((A - B).norm())
        for a, A in points.items()
        for b, B in points.items()
        if a != b
    }
    for name in (
        "AA_2C",
        "A_1CA_2",
        "OMC_1",
        "B_1MC",
        "DEA",
        "DED_1",
        "A_1HA",
        "DHD_1",
        "MCD",
        "KMC",
    ):
        names = re.findall(r"[A-Z](?:_[12])?", name)
        if not all(n in points for n in names):
            continue
        A, B, C = (points[n] for n in names)
        u, v = A - B, C - B
        c = sp.simplify(u.dot(v) / (u.norm() * v.norm()))
        values[r"\cos\angle " + name] = c
        values[r"\tan\angle " + name] = sp.simplify(u.cross(v).norm() / u.dot(v))
        values[r"\angle " + name] = sp.acos(c)
    return values | extra


def equal(a, b):
    if sp.simplify(a - b) == 0:
        return True
    return (
        (a.has(sp.acos, sp.atan) or b.has(sp.acos, sp.atan))
        and sp.simplify(sp.cos(a) - sp.cos(b)) == 0
        and 0 <= a <= sp.pi
        and 0 <= b <= sp.pi
    )


class ScalarParser(TrigonometricParser):
    implicit_prefixes = TrigonometricParser.implicit_prefixes + (r"\arccos", r"\arctan")

    def _nested(self, text):
        return ScalarParser(text).parse()

    def _primary(self):
        for command, function in ((r"\arccos", sp.acos), (r"\arctan", sp.atan)):
            if self.text.startswith(command, self.index):
                self.index += len(command)
                if self.text[self.index : self.index + 1] == "{":
                    argument, self.index = balanced(self.text, self.index)
                    value = self._nested(argument).value
                else:
                    value = self._primary().value
                return Node(function(value), "", "inverse")
        return super()._primary()


def evaluate(raw, values):
    for n in (2, 3):
        raw = raw.replace("\\sqrt" + str(n), r"\sqrt{" + str(n) + "}")
    raw = raw.replace("aH", "a H").replace("hS_", "h S_")
    raw = (
        substitute(raw, values)
        .replace(r"\operatorname{acos}", r"\arccos")
        .replace(r"\operatorname{atan}", r"\arctan")
    )
    return sp.simplify(ScalarParser(raw).parse().value)


def verify(html, m):
    points, extra, answer = geometry(m)
    values = values_for(points, extra)
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        if m.mode == "cube_projection_plane_angle" and formula.startswith("MD="):
            unit = {n: p / extra["a"] for n, p in points.items()}
            unit["K"] = (unit["B_1"] + unit["C"]) / 2
            values = values_for(unit, {"a": sp.S.One})
        for equation in formula.split(r",\qquad "):
            relations = re.split(r"(=|>)", equation)
            try:
                sides = [evaluate(side, values) for side in relations[::2]]
            except Exception as exc:
                raise AssertionError(
                    (formula, equation, substitute(equation, values))
                ) from exc
            assert len(sides) > 1, formula
            for i, relation in enumerate(relations[1::2]):
                assert (
                    equal(sides[i], sides[i + 1])
                    if relation == "="
                    else sp.simplify(sides[i] - sides[i + 1]).is_positive
                ), (formula, sides)
    assert equal(answer, m.answer), (answer, m.answer)
