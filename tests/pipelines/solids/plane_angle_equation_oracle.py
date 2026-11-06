"""Evaluate every displayed equation against independent geometry and frames."""

import re

import sympy as sp
from altitude_geometry_oracle import scalar, substitute
from bs4 import BeautifulSoup
from plane_angle_geometry import geometry


def evaluate(raw, values):
    raw = (
        raw.replace(r"\sqrt2", r"\sqrt{2}")
        .replace(r"\frac12", r"\frac{1}{2}")
        .replace(r"\,", "")
    )
    raw = raw.replace(r"\cos^2\varphi", r"(\cos\varphi)^2").replace(":", "/")
    raw = re.sub(
        r"\\tan\^2\\angle ([A-Z](?:_1)?[A-Z](?:_1)?[A-Z](?:_1)?)",
        r"(\\tan\\angle \1)^2",
        raw,
    )
    return scalar(substitute(raw, values))


def _coordinates(formula, frame, values):
    if re.match(r"[A-Z](?:_1)?\(", formula):
        for part in formula.split(r",\quad "):
            match = re.fullmatch(r"([A-Z](?:_1)?)\((.+)\)", part)
            assert match, formula
            actual = sp.Matrix([evaluate(c, values) for c in match[2].split(";")])
            assert sp.simplify(actual - frame[match[1]]) == sp.zeros(3, 1), (
                formula,
                actual,
                frame[match[1]],
            )
        return True
    if formula.startswith(r"\vec n_"):
        for part in formula.split(r",\qquad"):
            name, components = part.split("=")
            n = sp.Matrix(
                [evaluate(c, values) for c in components.strip()[1:-1].split(";")]
            )
            if name.strip() == r"\vec n_{\alpha}":
                for v in ("K", "P"):
                    assert sp.simplify(n.dot(frame[v] - frame["C_1"])) == 0
            else:
                for v in ("B", "B_1"):
                    assert sp.simplify(n.dot(frame[v] - frame["C_1"])) == 0
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
        if m.mode.startswith("cube_parallel") and formula.startswith("P("):
            a = dict(m.given)["a"]
            frame = {
                k: sp.Matrix([a - v[1], a - v[0], a - v[2]]) for k, v in points.items()
            }
        if _coordinates(formula, frame, values):
            continue
        expressions = (
            formula[len(r"\begin{cases}") : -len(r"\end{cases}")].split(r"\\")
            if formula.startswith(r"\begin{cases}")
            else formula.split(r",\qquad ")
        )
        for expression in expressions:
            data_sets = [values]
            if re.search(r"[xyz]", re.sub(r"\\[A-Za-z]+", "", expression)):
                data_sets = [
                    values | dict(zip("xyz", frame[key], strict=True))
                    for key in ("K", "P", "C_1")
                ]
            for data in data_sets:
                try:
                    sides = [evaluate(part, data) for part in expression.split("=")]
                except Exception as exc:
                    raise AssertionError((formula, expression)) from exc
                assert len(sides) > 1 and all(
                    sp.simplify(v - sides[0]) == 0 for v in sides
                ), (formula, sides)
    assert sp.simplify(answer - m.answer) == 0, (answer, m.answer)
    return sp.simplify(answer)
