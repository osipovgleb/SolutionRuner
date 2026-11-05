"""Check volume by independent horizontal slices and evaluate every proof equality."""

import itertools
import re

import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import solution_html
from sphere_formula_oracle import PiParser
from sympy.geometry import Point2D, Polygon, convex_hull


def coordinates(m):
    root = sp.sqrt(3)
    base = (
        [(0, 0), (2, 0), (1, root)]
        if m.body == "triangle"
        else [(2, 0), (1, root), (-1, root), (-2, 0), (-1, -root), (1, -root)]
    )
    full = Polygon(*(Point2D(*p) for p in base)).area
    scale = sp.sqrt(m.given[0] / full)
    return {
        chr(65 + i) + ("_1" if level else ""): sp.Matrix(
            (x * scale, y * scale, level * m.given[1])
        )
        for level in (0, 1)
        for i, (x, y) in enumerate(base)
    }


def area(points, names):
    return sp.Abs(Polygon(*(Point2D(*points[n][:2]) for n in names)).area)


def sliced_volume(points, names, height):
    lower = [points[n] for n in names if not n.endswith("_1")]
    upper = [points[n] for n in names if n.endswith("_1")]

    def cross_section(t):
        ps = {
            Point2D(*(a * (1 - t) + b * t)[:2])
            for a, b in itertools.product(lower, upper)
        }
        hull = convex_hull(*ps)
        return sp.Abs(hull.area) if isinstance(hull, Polygon) else sp.S.Zero

    # Two horizontal vertex layers give Minkowski polygon sections with quadratic area.
    return sp.simplify(
        height
        * (cross_section(0) + 4 * cross_section(sp.Rational(1, 2)) + cross_section(1))
        / 6
    )


def verify(result, m):
    points = coordinates(m)
    b, h = m.given
    expected = sliced_volume(points, m.vertices, h)
    assert sp.simplify(PiParser(result.answer).parse().value - expected) == 0
    edge = sp.sqrt((points["B"] - points["A"]).dot(points["B"] - points["A"]))
    variables = {
        "B": b,
        "H": h,
        "B_p": area(points, m.base) if m.base else b,
        "h_p": h,
        "a": edge,
        "T": sp.sqrt(3) * edge**2 / 4,
        "V": expected,
        "V_0": b * h,
    }
    for i, removed in enumerate(m.removed, 1):
        variables["V_" + str(i)] = sliced_volume(points, removed, h)
    html = BeautifulSoup(solution_html(result), "html.parser")
    nodes = html.select("center [data-inline-latex]")
    assert 5 <= len(nodes) <= 9
    for node in nodes:
        formula = node["data-inline-latex"]
        for names in re.findall(r"S_\{([A-F]{3})\}", formula):
            formula = formula.replace(
                "S_{" + names + "}", "(" + sp.latex(area(points, names)) + ")"
            )
        formula = formula.replace(r"\sin120^{\circ}", r"\cdot\frac{\sqrt{3}}{2}")
        for before, after in (
            ("B_ph_p", r"B_p\cdot h_p"),
            ("B_pH", r"B_p\cdot H"),
            ("BH", r"B\cdot H"),
        ):
            formula = formula.replace(before, after)
        for name, amount in sorted(variables.items(), key=lambda item: -len(item[0])):
            formula = re.sub(
                r"(?<![A-Za-z_\\])" + re.escape(name) + r"(?![A-Za-z_0-9])",
                lambda _, v=amount: "(" + sp.latex(v) + ")",
                formula,
            )
        formula = re.sub(r"\)(?=\(|\\frac)", r")\\cdot ", formula)
        values = [PiParser(s).parse().value for s in formula.split("=")]
        assert len(values) > 1 and all(
            sp.simplify(v - values[0]) == 0 for v in values
        ), formula
    assert "вектор" not in html.get_text().lower()
