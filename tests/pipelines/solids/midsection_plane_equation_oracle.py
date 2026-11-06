"""Every displayed scalar, plane-normal and coordinate equation is independently checked."""

import re

import sympy as sp
from altitude_geometry_oracle import scalar, substitute
from bs4 import BeautifulSoup
from midsection_plane_geometry import geometry


def evaluate(raw, values):
    if raw.startswith("|") and raw.endswith("|"):
        return abs(evaluate(raw[1:-1], values))
    raw = raw.replace(r"\sqrt3", r"\sqrt{3}").replace(
        r"\cos^2\varphi", r"(\cos\varphi)^2"
    )
    return scalar(substitute(raw, values))


def coordinates(formula, points, values):
    if re.match(r"[A-Z](?:_1)?\(", formula):
        for part in formula.split(r",\quad "):
            m = re.fullmatch(r"([A-Z](?:_1)?)\((.+)\)", part)
            assert m, formula
            actual = sp.Matrix([evaluate(c, values) for c in m[2].split(";")])
            assert sp.simplify(actual - points[m[1]]) == sp.zeros(3, 1), formula
        return True
    if formula.startswith(r"\vec n_"):
        for part in formula.split(r",\qquad "):
            name, raw = part.split("=")
            n = sp.Matrix([evaluate(c, values) for c in raw[1:-1].split(";")])
            reference = "B"
            others = ("E", "D_1") if name == r"\vec n_{BED_1}" else ("A", "C")
            for key in others:
                assert sp.simplify(n.dot(points[key] - points[reference])) == 0, formula
        return True
    return False


def verify(html, m):
    points, extra, answer = geometry(m)
    values = {
        a + b: sp.simplify((A - B).norm())
        for a, A in points.items()
        for b, B in points.items()
        if a != b
    } | extra
    frame = points
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        if m.mode == "square_prism_opposite_vertex_plane_angle" and formula.startswith(
            "A("
        ):
            a = dict(m.given)["a"]
            frame = {k: sp.Matrix([p[1], a - p[0], p[2]]) for k, p in points.items()}
        if coordinates(formula, frame, values):
            continue
        equations = (
            formula[len(r"\begin{cases}") : -len(r"\end{cases}")].split(r"\\")
            if formula.startswith(r"\begin{cases}")
            else formula.split(r",\qquad ")
        )
        for equation in equations:
            try:
                sides = [evaluate(x, values) for x in equation.split("=")]
            except Exception as exc:
                raise AssertionError((formula, equation)) from exc
            assert len(sides) > 1 and all(
                sp.simplify(v - sides[0]) == 0 for v in sides
            ), (formula, sides)
    assert sp.simplify(answer - m.answer) == 0, (answer, m.answer)
    return answer
