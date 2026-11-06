"""Check the projection proofs against independent coordinates, including child alternatives."""

import re

import sympy as sp
from altitude_geometry_oracle import substitute
from bs4 import BeautifulSoup
from plane_geometry_oracle import foot
from projection_plane_equation_oracle import equal, evaluate, values_for
from test_line_projection_models import coordinates, normal


def geometry(m):
    g = dict(m.given)
    p = coordinates(g["a"], g["b"], g.get("height", g.get("H")))
    if m.mode == "box_tetrahedron_line_projection_angle":
        p["H"] = (
            foot(p["C_1"], p["C"], p["D_1"])
            if m.names[0] == "face"
            else foot(p["B"], p["A"], p["C"])
        )
    else:
        p["S"] = p["A_1"]
        p.update(E=2 * p["B"], O=(p["A"] + p["C"]) / 2, K=(p["S"] + p["A"]) / 2)
    values = values_for(p, {})
    for label in ("C_1BH", "BA_1H", "CSB", "SCE", "BOK"):
        names = re.findall(r"[A-Z](?:_1)?", label)
        if not all(n in p for n in names):
            continue
        A, B, C = (p[n] for n in names)
        u, v = A - B, C - B
        values[r"\sin\angle " + label] = sp.simplify(
            u.cross(v).norm() / (u.norm() * v.norm())
        )
        values[r"\cos\angle " + label] = sp.simplify(u.dot(v) / (u.norm() * v.norm()))
        values[r"\tan\angle " + label] = sp.simplify(u.cross(v).norm() / u.dot(v))
        values[r"\angle " + label] = sp.acos(values[r"\cos\angle " + label])
    if m.mode == "rectangular_pyramid_angle":
        values[r"\angle CSB"] *= 180 / sp.pi
    return p, values


def scalar(raw, values):
    raw = substitute(raw, values)
    raw = re.sub(
        r"\|([^|]+)\|", lambda x: "(" + sp.latex(abs(evaluate(x[1], values))) + ")", raw
    )
    return evaluate(raw, values)


def verify_coordinates(formula, p, values):
    frame = {n: sp.Matrix([v[1], v[0], v[2]]) for n, v in p.items()}
    if formula.startswith("S("):
        for component in formula.split(r",\quad "):
            name, text = component.split("(", 1)
            point = sp.Matrix([scalar(x, values) for x in text[:-1].split(";")])
            assert sp.simplify(point - frame[name]) == sp.zeros(3, 1)
        return True
    if formula.startswith(r"\overrightarrow{"):
        for component in formula.split(r",\qquad "):
            name, text = component.removeprefix(r"\overrightarrow{").split("}=", 1)
            a, b = name
            vector = sp.Matrix([scalar(x, values) for x in text[1:-1].split(";")])
            assert sp.simplify(vector - frame[b] + frame[a]) == sp.zeros(3, 1)
        return True
    return False


def verify(html, m):
    p, values = geometry(m)
    if m.mode == "rectangular_pyramid_proved_altitude_angle":
        u, v = p["C"] - p["S"], p["D"] - p["B"]
        values[r"\cos\alpha"] = sp.simplify(abs(u.dot(v)) / (u.norm() * v.norm()))
        values[
            r"\frac{|\overrightarrow{SC}\cdot\overrightarrow{BD}|}{|\overrightarrow{SC}|\cdot|\overrightarrow{BD}|}"
        ] = values[r"\cos\alpha"]
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        if verify_coordinates(formula, p, values):
            continue
        for equation in formula.split(r",\qquad "):
            try:
                sides = [scalar(x, values) for x in equation.split("=")]
                if m.mode == "rectangular_pyramid_angle" and equation.startswith(
                    r"\angle CSB="
                ):
                    sides = [sp.simplify(x * sp.pi / 180) for x in sides]
            except Exception as exc:
                raise AssertionError((formula, equation)) from exc
            assert len(sides) > 1 and all(equal(x, sides[0]) for x in sides), (
                formula,
                sides,
            )
    if m.mode == "box_tetrahedron_line_projection_angle":
        vector = p["C_1"] - p["B"] if m.names[0] == "face" else p["B"] - p["A_1"]
        n = normal(p, ("A_1", "B", "C") if m.names[0] == "face" else ("A", "A_1", "C"))
        assert (
            sp.simplify(
                sp.sin(m.answer) - abs(vector.dot(n)) / (vector.norm() * n.norm())
            )
            == 0
        )
