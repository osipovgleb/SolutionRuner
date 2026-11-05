"""Verify every published equality against independent solid geometry and givens."""

import re

import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import solution_html
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.probability.common import UnsupportedCondition
from solution_runner.pipelines.solids.combined_ratio_proofs import SC, SS, VC, VK, VS


def ratios(m):
    k, g = m.kind, m.given
    if k in {"sphere_cylinder_surface", "cylinder_sphere_surface"}:
        r = sp.sqrt(g[0] / ((6 if k == "sphere_cylinder_surface" else 4) * sp.pi))
        v = {"r": r, "h": 2 * r, SC: 6 * sp.pi * r**2, SS: 4 * sp.pi * r**2}
        return v, v[SS if k == "sphere_cylinder_surface" else SC]
    if k in {"sphere_cylinder_volume", "cylinder_sphere_volume"}:
        r = sp.root(
            g[0]
            / ((2 if k == "sphere_cylinder_volume" else sp.Rational(4, 3)) * sp.pi),
            3,
        )
        v = {"R": r, "h": 2 * r, VC: 2 * sp.pi * r**3, VS: 4 * sp.pi * r**3 / 3}
        return v, v[VS if k == "sphere_cylinder_volume" else VC]
    if k in {"cylinder_cone_volume", "cone_cylinder_volume"}:
        h = g[0] * (3 if k == "cylinder_cone_volume" else 1) / 2
        v = {"B": 2, "h": h, VC: 2 * h, VK: 2 * h / 3}
        return v, v[VC if k == "cylinder_cone_volume" else VK]
    if k in {"cone_sphere_volume", "sphere_cone_volume"}:
        r = sp.root(
            g[0] * (sp.Rational(3, 4) if k == "cone_sphere_volume" else 3) / sp.pi, 3
        )
        v = {"R": r, "h": r, VS: 4 * sp.pi * r**3 / 3, VK: sp.pi * r**3 / 3}
        return v, v[VK if k == "cone_sphere_volume" else VS]
    if k == "cone_cylinder_lateral":
        r = sp.sqrt(g[0] / (2 * sp.pi))
        v = {
            "r": r,
            "h": r,
            "l": sp.sqrt(2) * r,
            SC: 2 * sp.pi * r**2,
            r"S_{\mathrm{кон}}": sp.pi * sp.sqrt(2) * r**2,
        }
        return v, v[r"S_{\mathrm{кон}}"]
    if k in {
        "pyramid_cones_ratio",
        "pyramid_outer_cone_volume",
        "pyramid_inner_cone_volume",
    }:
        h = (
            sp.S.One
            if not g
            else 3 * g[0] / (sp.pi * (1 if k == "pyramid_outer_cone_volume" else 2))
        )
        v = {
            "a": 2,
            "d_1": 2,
            "d_2": 2 * sp.sqrt(2),
            "V_1": sp.pi * h / 3,
            "V_2": 2 * sp.pi * h / 3,
        }
        return v, sp.Integer(2) if not g else v[
            "V_2" if k == "pyramid_outer_cone_volume" else "V_1"
        ]
    if k in {"tetra_midpoint_volume", "tetra_midpoint_surface"}:
        s = "V" if k.endswith("volume") else "S"
        v = {
            "k": sp.Rational(1, 2),
            s + "_0": g[0],
            s + "_1": g[0] / (8 if s == "V" else 4),
            s: g[0] / 2,
        }
        return v, v[s]
    return None


def cubes(m):
    k, q, g = m.kind, m.q, m.given
    if k == "cube_sphere_volume":
        r3 = 3 * g[0] / (4 * sp.pi)
        assert q["r3"] == r3
        return {
            "R": sp.root(r3, 3),
            "a": 2 * sp.root(r3, 3),
            r"V_{\mathrm{ш}}": g[0],
            r"V_{\mathrm{к}}": 8 * r3,
        }, 8 * r3
    if k in {"sphere_vertex_part", "sphere_edge_part"}:
        a, r = g[0], g[0] if k == "sphere_vertex_part" else g[1]
        fraction = sp.Rational(1, 8) if k == "sphere_vertex_part" else sp.Rational(1, 4)
        assert r <= a if k == "sphere_vertex_part" else 2 * r <= a
        return {
            "a": a,
            "r": r,
            "S_0": 4 * sp.pi * r**2,
            "S": fraction * 4 * sp.pi * r**2,
        }, fraction * 4 * r**2
    if k == "cube_prism_hole":
        b, h = g
        assert 0 < b < 1 and h == 1
        s = 6 - 2 * b * b + 4 * b
        return {"b": b, "h": h, "L": 4 * b, "B": b * b, "S_0": 6, "S": s}, s
    if k not in {
        "cube_around_sphere_volume",
        "cube_around_sphere_surface",
        "cube_insphere_radius",
        "cube_insphere_volume",
        "cube_circumsphere_volume",
        "cube_in_sphere_volume",
    }:
        return None
    a, r = q["a"], q["r"]
    if k in {"cube_around_sphere_volume", "cube_around_sphere_surface"}:
        assert r == g[0] and a == 2 * r
    elif k == "cube_insphere_radius":
        assert a**3 == g[0] and r == a / 2
    elif k == "cube_in_sphere_volume":
        assert r == g[0] and sp.simplify(a * sp.sqrt(3) - 2 * r) == 0
    else:
        assert a == g[0]
        assert (
            sp.simplify(
                2 * r - a * (sp.sqrt(3) if k == "cube_circumsphere_volume" else 1)
            )
            == 0
        )
    sphere = k in {"cube_insphere_volume", "cube_circumsphere_volume"}
    volume = 4 * sp.pi * r**3 / 3 if sphere else a**3
    v = {"a": a, "r": r, "R": r, "d": a * sp.sqrt(3), "V": volume, "S": 6 * a**2}
    answer = (
        r
        if k == "cube_insphere_radius"
        else 6 * a**2
        if k.endswith("surface")
        else volume / sp.pi
        if sphere
        else volume
    )
    return v, answer


def prisms(m):
    k, q, g = m.kind, m.q, m.given
    if k in {"box_cylinder_volume", "box_cylinder_height"}:
        r, a, h, b = q["r"], q["a"], q["H"], q["B"]
        assert r == g[0] and a == 2 * r and b == a**2
        assert h == g[1] if k.endswith("volume") else b * h == g[1]
        return {"a": a, "r": r, "H": h, "B": b, "V": b * h}, h if k.endswith(
            "height"
        ) else b * h
    if k in {"cylinder_around_triangle", "cylinder_around_square"}:
        a = g[0]
        b = g[1] if k.endswith("triangle") else a
        d = sp.sqrt(a**2 + b**2)
        h = g[-1] / sp.pi
        assert q["d2"] == d**2 and q["H"] == h
        volume = sp.pi * (d / 2) ** 2 * h
        return {"a": a, "b": b, "d": d, "H": h, "V": volume}, volume
    if k in {
        "square_cylinder_lateral",
        "square_cylinder_height",
        "triangle_around_cylinder_lateral",
        "triangle_in_cylinder_lateral",
        "hexagon_cylinder_lateral",
    }:
        n = 6 if k.startswith("hexagon") else 4 if k.startswith("square") else 3
        a, r, h = q["a"], q["r"], q["H"]
        radius = (
            a / (2 * sp.sin(sp.pi / n))
            if k == "triangle_in_cylinder_lateral"
            else a / (2 * sp.tan(sp.pi / n))
        )
        assert sp.simplify(radius - r) == 0 and r == g[0]
        assert q["P"] == n * a
        assert n * a * h == g[1] if k.endswith("height") else h == g[1]
        v = {"a": a, "r": r, "H": h, "P": n * a, "L": n * a * h}
        return v, h if k.endswith("height") else v["L"]
    if k == "pyramid_cone_volume":
        a, h = g
        r = a / sp.sqrt(2)
        assert sp.simplify(q["r"] - r) == 0
        volume = sp.pi * r**2 * h / 3
        return {
            "a": a,
            "r": r,
            "d": a * sp.sqrt(2),
            "H": h,
            "V": volume,
        }, volume / sp.pi
    if k in {"cone_sphere_radius", "cone_sphere_slant"}:
        r, l = q["r"], q["l"]
        assert sp.simplify(l**2 - 2 * r**2) == 0
        assert l == g[0] if k.endswith("radius") else r == g[0]
        return {"r": r, "h": r, "l": l}, r if k.endswith("radius") else l
    raise AssertionError((k, "independent geometry missing"))


def verify(result, m):
    variables, answer = ratios(m) or cubes(m) or prisms(m)
    html = solution_html(result)
    nodes = BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    assert 5 <= len(nodes) <= 9, (m.kind, len(nodes))
    for node in nodes:
        formula = node["data-inline-latex"]
        for pair in ("Bh", "BH", "PH", "rh", "rl", "bh"):
            formula = formula.replace(pair, pair[0] + r"\cdot " + pair[1])
        for name, amount in sorted(variables.items(), key=lambda item: -len(item[0])):
            formula = re.sub(
                r"(?<![A-Za-z_\\])" + re.escape(name) + r"(?![A-Za-z_0-9])",
                lambda _, v=amount: "(" + sp.latex(sp.sympify(v)) + ")",
                formula,
            )
        formula = formula.replace(r"\pi", r"(\pi)")
        try:
            terms = [PiParser(v).parse().value for v in formula.split("=")]
        except UnsupportedCondition as exc:
            raise AssertionError((m.kind, formula)) from exc
        assert len(terms) >= 2 and all(sp.simplify(t - terms[0]) == 0 for t in terms), (
            m.kind,
            formula,
        )
    assert sp.simplify(PiParser(result.answer).parse().value - answer) == 0, (
        m.kind,
        result.answer,
        answer,
    )
