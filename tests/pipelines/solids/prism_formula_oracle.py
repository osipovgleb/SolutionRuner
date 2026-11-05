"""Evaluate every published equality using independent base formulas and pyramid determinants."""

import re

import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import solution_html
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.solids.box_coordinates import VERTICES


def _measured(m):
    g = m.given
    a = g[0]
    kind = m.kind
    if m.base == "triangle":
        b = g[1]
        c = sp.sqrt(a * a + b * b)
        base = a * b / 2
        perimeter = a + b + c
        params = {"a": a, "b": b, "c": c}
    elif m.base == "rhombus":
        d1, d2 = g[:2]
        side = sp.sqrt(d1 * d1 + d2 * d2) / 2
        base = d1 * d2 / 2
        perimeter = 4 * side
        params = {"a": side, "d_1": d1, "d_2": d2}
    else:
        base = a * a if m.base == "square" else 3 * sp.sqrt(3) * a * a / 2
        perimeter = (4 if m.base == "square" else 6) * a
        params = {"a": a}
    height = g[-1]
    if kind == "triangle_height_volume":
        height = g[-1] / base
    elif kind.endswith("height_total"):
        height = (g[-1] - 2 * base) / perimeter
    surface = (
        perimeter * height
        if kind in {"hex_lateral", "normal_lateral"}
        else 2 * base + perimeter * height
    )
    params.update(
        B=base,
        P=perimeter,
        H=height,
        L=height,
        V=base * height,
        S=surface,
        S_f=a * height,
    )
    expected = (
        height
        if "height" in kind
        else surface
        if kind.endswith(("total", "lateral"))
        else base * height
    )
    return params, sp.simplify(expected)


def _pyramid(m):
    base, height = m.given
    a = sp.sqrt(base)

    def point(name):
        x, y, z = VERTICES[name]
        return sp.Matrix([a * x, a * y, height * z])

    apex = point(m.solid.apex)
    vectors = [point(n) - apex for n in m.solid.base]
    volume = (
        sp.Abs(
            sum(
                sp.det(sp.Matrix.hstack(vectors[0], vectors[i], vectors[i + 1]))
                for i in range(1, len(vectors) - 1)
            )
        )
        / 6
    )
    origin = point(m.solid.base[0])
    normal = (point(m.solid.base[1]) - origin).cross(point(m.solid.base[2]) - origin)
    length = sp.sqrt(normal.dot(normal))
    altitude = sp.Abs((apex - origin).dot(normal)) / length
    area = 3 * volume / altitude
    return {
        "B": base,
        "H": height,
        "a": a,
        "B_p": area,
        "h_p": altitude,
        "V": volume,
    }, volume


def _ratios(m):
    given = m.given[0]
    kind = m.kind
    if kind == "transfer":
        q = m.ratio
        h1 = given
        h2 = h1 / q**2
        a1 = sp.Integer(2)
        a2 = a1 * q
        b1 = sp.sqrt(3) * a1 * a1 / 4
        b2 = sp.sqrt(3) * a2 * a2 / 4
        return {
            "a_1": a1,
            "a_2": a2,
            "B_1": b1,
            "B_2": b2,
            "H_1": h1,
            "H_2": h2,
            "V": b1 * h1,
        }, h2
    if kind == "similar_surface":
        return {
            "k": m.ratio,
            "S_0": given,
            "S_1": given * m.ratio**2,
        }, given * m.ratio**2
    if kind == "remove_pyramid":
        return {
            "B": given,
            "H": sp.S.One,
            "V_0": given,
            "V_p": given / 3,
            "V": given * 2 / 3,
        }, given * 2 / 3
    volume = "volume" in kind or kind in {"cube_part", "cube_whole"}
    small_fraction = (
        sp.Rational(1, 8)
        if kind.startswith("cube")
        else sp.Rational(1, 4)
        if volume
        else sp.Rational(1, 2)
    )
    whole = given / small_fraction if kind.endswith("whole") else given
    small = whole * small_fraction
    symbol = "V" if volume else "S"
    p = {
        "k": sp.Rational(1, 2),
        "B_0": whole,
        "B_1": small,
        "B_t": whole / 2,
        "H_0": sp.S.One,
        "H_1": sp.S.One,
        "P_0": whole,
        "P_1": whole / 2,
        symbol + "_0": whole,
        symbol + "_1": small,
    }
    return p, whole if kind.endswith("whole") else small


def quantities(m):
    if m.base and m.kind not in {"oblique_rhombus", "oblique_hex"}:
        return _measured(m)
    if m.kind == "vertex_volume":
        return _pyramid(m)
    if m.kind in {"midline_section", "median_section"}:
        a, h = m.given
        ae = a / 2
        width = a / 2 if m.kind == "midline_section" else sp.sqrt(a * a - ae * ae)
        return {"a": a, "H": h, "AE": ae, "l": width, "S": width * h}, width * h
    if m.kind == "diagonal_section":
        h, d = m.given
        t = sp.sqrt((d - h) * (d + h))
        return {"H": h, "D": d, "BD_1": d, "A_1C": d, "t": t, "S": t * h}, t * h
    if m.kind in {"oblique_rhombus", "oblique_hex"}:
        a = m.given[0]
        alpha = m.given[-1]
        edge = m.given[2] if m.kind == "oblique_rhombus" else m.given[1]
        beta = m.given[1] if m.kind == "oblique_rhombus" else sp.S.Zero
        base = (
            a * a * sp.sin(sp.pi * beta / 180)
            if m.kind == "oblique_rhombus"
            else 3 * sp.sqrt(3) * a * a / 2
        )
        h = edge * sp.sin(sp.pi * alpha / 180)
        return {
            "a": a,
            "L": edge,
            "H": h,
            "B": base,
            "V": base * h,
            r"\alpha": alpha,
            r"\beta": beta,
            r"\sin\alpha": sp.sin(sp.pi * alpha / 180),
            r"\sin\beta": sp.sin(sp.pi * beta / 180),
        }, base * h
    return _ratios(m)


def verify(result, m):
    variables, expected = quantities(m)
    nodes = BeautifulSoup(solution_html(result), "html.parser").select(
        "[data-inline-latex]"
    )
    assert 5 <= len(nodes) <= 9
    for node in nodes:
        formula = node["data-inline-latex"]
        formula = re.sub(
            r"\\sin\s+(\d+)\^\\circ",
            lambda z: "(" + sp.latex(sp.sin(sp.pi * int(z[1]) / 180)) + ")",
            formula,
        )
        formula = formula.replace(r"^\circ", "")
        for old, new in [
            ("B_ph_p", r"B_p\cdot h_p"),
            ("B_1H_1", r"B_1\cdot H_1"),
            ("B_2H_2", r"B_2\cdot H_2"),
            (r"L\sin", r"L\cdot \sin"),
            ("B_0H_0", r"B_0\cdot H_0"),
            ("BH", r"B\cdot H"),
            ("PH", r"P\cdot H"),
            ("PL", r"P\cdot L"),
            ("ab", r"a\cdot b"),
            ("d_1d_2", r"d_1\cdot d_2"),
            ("aH", r"a\cdot H"),
            ("lH", r"l\cdot H"),
            ("Ht", r"H\cdot t"),
            ("kP_0", r"k\cdot P_0"),
            ("kS_0", r"k\cdot S_0"),
        ]:
            formula = formula.replace(old, new)
        for name, amount in sorted(variables.items(), key=lambda p: -len(p[0])):
            formula = re.sub(
                r"(?<![A-Za-z_\\])" + re.escape(name) + r"(?![A-Za-z_0-9])",
                lambda _, v=amount: "(" + sp.latex(v) + ")",
                formula,
            )
        values = [PiParser(v).parse().value for v in formula.split("=")]
        assert len(values) > 1 and all(
            sp.simplify(v - values[0]) == 0 for v in values
        ), formula
    assert sp.simplify(PiParser(result.answer).parse().value - expected) == 0
