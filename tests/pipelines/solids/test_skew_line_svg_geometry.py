"""Reconstruct the generated cameras and validate actual 3D feet and axis directions."""

import math
import re
import xml.etree.ElementTree as ET

import pytest
import sympy as sp
from skew_line_equation_oracle import evaluate
from skew_line_geometry import geometry
from skew_line_source_cases import CASES, GROUPS, read
from test_line_projection_generated import endpoint

from solution_runner.pipelines.core.handler_registry import get_handler

NS = "{http://www.w3.org/2000/svg}"


def figures(task):
    case = next(c for c in CASES if c["task"] == task)
    return case, {
        s["asset_key"]: ET.fromstring(s["svg_text"])
        for s in get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(
            case["context"]
        )
    }


@pytest.mark.parametrize("slot", (1, 2, 3))
def test_each_prism_illustration_uses_actual_midpoints_and_directions(slot):
    case, roots = figures("530402")
    root = roots["box_distance_solution_" + str(slot)]
    p, _ = geometry(read(case))
    O = endpoint(root, "wire-A-B", 1)
    B = endpoint(root, "wire-A-B", 2)
    C = endpoint(root, "wire-B-C", 2)
    A1 = endpoint(root, "wire-A-A_1", 2)
    X = (C - O) / p["C"][0]
    Y = (B - O - p["B"][0] * X) / p["B"][1]
    Z = (A1 - O) / p["A_1"][2]
    camera = sp.Matrix.hstack(X, Y, Z)
    for a, b in (("K", "N"), ("K", "M"), ("N", "M")):
        for i, name in enumerate((a, b), 1):
            assert (
                max(
                    abs(float(x))
                    for x in endpoint(root, "helper-" + a + "-" + b, i)
                    - O
                    - camera * p[name]
                )
                < 4e-6
            )
    assert all(e.get("id") for e in root.iter(NS + "line"))
    if slot == 2:
        for name, end in (("a", "A"), ("b", "C"), ("c", "B_1")):
            assert (
                max(
                    abs(float(x))
                    for x in endpoint(root, "vector-" + name, 1) - O - camera * p["B"]
                )
                < 4e-6
            )
            assert (
                max(
                    abs(float(x))
                    for x in endpoint(root, "vector-" + name, 2) - O - camera * p[end]
                )
                < 4e-6
            )
    if slot == 3:
        for j, name in enumerate("xyz"):
            v = endpoint(root, "axis-" + name, 2) - O
            direction = camera[:, j]
            assert (
                abs(float(sp.det(sp.Matrix.hstack(v, direction)) / direction.norm()))
                < 4e-6
            )
            assert float(v.dot(direction)) > 0
    if slot == 1:
        u, v = p["M"] - p["H"], p["A"] - p["H"]
        assert sp.simplify(u.dot(v)) == 0
        frame = camera * sp.Matrix.hstack(u / u.norm(), v / v.norm())
        base = O + camera * p["H"]
        marks = [
            endpoint(root, "right-angle-0-0", 1),
            endpoint(root, "right-angle-0-0", 2),
            endpoint(root, "right-angle-0-1", 2),
        ]
        recovered = [frame.inv() * (x - base) for x in marks]
        assert abs(float(recovered[0][1])) < 1e-5 and abs(float(recovered[2][0])) < 1e-5
        assert math.isclose(
            float(recovered[0][0]), float(recovered[1][0]), abs_tol=1e-5
        )
        assert math.isclose(
            float(recovered[2][1]), float(recovered[1][1]), abs_tol=1e-5
        )


def test_flat_triangle_lengths_and_arc_match_the_independent_pyramid():
    case, roots = figures("511402")
    root = roots["box_distance_solution_2"]
    p, _ = geometry(read(case))
    B = endpoint(root, "triangle-B-M", 1)
    M = endpoint(root, "triangle-B-M", 2)
    N = endpoint(root, "triangle-M-N", 2)
    ratios = [
        float((x - y).norm() / (p[a] - p[b]).norm())
        for x, y, a, b in ((B, M, "B", "M"), (M, N, "M", "N"), (B, N, "B", "N"))
    ]
    assert max(ratios) - min(ratios) < 2e-6
    for i, edge in enumerate((("B", "M"), ("M", "N"), ("B", "N"))):
        text = root.find(f"{NS}text[@id='length-{i}']").text
        scalar = re.sub(r"√(\d+)", r"\\sqrt{\1}", text).replace("·", r"\cdot")
        assert (
            sp.simplify(evaluate(scalar, {}, {}) - (p[edge[0]] - p[edge[1]]).norm())
            == 0
        )
    arc = [
        sp.Matrix([float(x) for x in xy.split(",")])
        for xy in root.find(f"{NS}polyline[@id='midpoint-angle']").get("points").split()
    ]
    radii = [float((x - M).norm()) for x in arc]
    assert max(radii) - min(radii) < 2e-6
    u, v = B - M, N - M
    expected_cosine = float(
        (p["B"] - p["M"]).dot(p["N"] - p["M"])
        / ((p["B"] - p["M"]).norm() * (p["N"] - p["M"]).norm())
    )
    actual_cosine = float(u.dot(v) / (u.norm() * v.norm()))
    assert math.isclose(actual_cosine, expected_cosine, abs_tol=1e-7)
    assert abs(float(sp.det(sp.Matrix.hstack(arc[0] - M, u)) / u.norm())) < 4e-6
    assert abs(float(sp.det(sp.Matrix.hstack(arc[-1] - M, v)) / v.norm())) < 4e-6
