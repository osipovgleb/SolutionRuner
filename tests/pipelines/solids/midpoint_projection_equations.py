"""Check every displayed equation against an independently reconstructed solid."""

import re

import sympy as sp
from bs4 import BeautifulSoup
from midpoint_projection_geometry import geometry
from projection_plane_equation_oracle import equal, evaluate, values_for

from solution_runner.pipelines.solids.spatial_distance_proofs import render


def verify(m, html=None):
    p, independent = geometry(m)
    values = values_for(p, {})
    for name in ("EFB", "EFA_1", "MNM_1", "A_1BM", "C_1BH"):
        names = re.findall(r"[A-Z](?:_1)?", name)
        if not all(n in p for n in names):
            continue
        A, B, C = (p[n] for n in names)
        u, v = A - B, C - B
        values[r"\tan\angle " + name] = sp.simplify(u.cross(v).norm() / u.dot(v))
        values[r"\sin\angle " + name] = sp.simplify(
            u.cross(v).norm() / (u.norm() * v.norm())
        )
    if m.mode == "symmetric_tetrahedron_line_plane_angle":
        values["x"] = sp.simplify(
            (p["M"] - p["S"]).dot(p["N"] - p["S"]) / (p["N"] - p["S"]).norm()
        )
        values[r"\cos\alpha"] = sp.cos(independent)
    if m.mode == "triangle_pyramid_parallel_rectangle_distance":
        values["x"] = (p["B"] - p["T"]).norm()
        values[r"d(S,\omega)"] = independent
    html = render(m, {}) if html is None else html
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("[data-inline-latex]"):
        formula = node["data-inline-latex"].replace("{,}", ".")
        for equation in formula.split(r",\qquad "):
            sides = [evaluate(x, values) for x in equation.split("=")]
            assert len(sides) > 1 and all(equal(x, sides[0]) for x in sides), (
                formula,
                sides,
            )
    assert "\\" not in soup.get_text()
    assert equal(independent, m.answer)
    return html
