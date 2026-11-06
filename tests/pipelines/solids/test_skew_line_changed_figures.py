"""Changed dimensions require valid foot order and actual acute, right or obtuse triangles."""

import hashlib
import xml.etree.ElementTree as ET

import pytest
import sympy as sp
from midpoint_source_cases import replay, solution_html
from skew_line_equation_oracle import verify
from skew_line_geometry import geometry
from skew_line_source_cases import CASES, GROUPS, changed, plan, read
from test_line_projection_generated import endpoint

from solution_runner.pipelines.core.handler_registry import get_handler

SAMPLES = [
    (
        "699395",
        [("AB = 9", "AB = 5"), ("AC = 12", "AC = 8"), ("AA_1 = 3", "AA_1 = 6")],
        1,
    ),
    (
        "699395",
        [("AB = 9", "AB = 13"), ("AC = 12", "AC = 10"), ("AA_1 = 3", "AA_1 = 5")],
        0,
    ),
    ("530402", [("AB = 8", "AB = 5"), ("AA_1 = 3", "AA_1 = 2,5")], 3),
    ("505387", [(r"\frac{1}{9}", "0")], 1),
    ("505387", [(r"\frac{1}{9}", r"-\frac{1}{4}")], 1),
    ("505408", [(r"\frac{17}{25}", "-0,4")], 1),
]


@pytest.mark.parametrize("task,replacements,count", SAMPLES)
def test_changed_full_plan_keeps_each_figure_and_verifies_all_equations(
    task, replacements, count
):
    original = next(c for c in CASES if c["task"] == task)
    case = changed(original, replacements)
    specs = get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(case["context"])
    assert len(specs) == count
    result = plan(case)
    verify(solution_html(result), read(case))
    for spec in specs:
        assert spec["sha256"] == hashlib.sha256(spec["svg_text"].encode()).hexdigest()
        root = ET.fromstring(spec["svg_text"])
        ids = [e.get("id") for e in root.iter() if e.get("id")]
        assert len(ids) == len(set(ids))
    replay(case["context"], result.transformations)
    assert not plan(case).transformations


def test_external_foot_is_projected_beyond_b_and_the_base_edge_is_extended():
    original = next(c for c in CASES if c["task"] == "699395")
    case = changed(original, SAMPLES[0][1])
    p, _ = geometry(read(case))
    assert (p["E"] - p["B"]).dot(p["B"] - p["A"]) > 0
    (spec,) = get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(case["context"])
    root = ET.fromstring(spec["svg_text"])
    O = endpoint(root, "wire-A-B", 1)
    B = endpoint(root, "wire-A-B", 2)
    C = endpoint(root, "wire-B-C", 2)
    A1 = endpoint(root, "wire-A-A_1", 2)
    X = (C - O) / p["C"][0]
    Y = (B - O - p["B"][0] * X) / p["B"][1]
    camera = sp.Matrix.hstack(X, Y, (A1 - O) / p["A_1"][2])
    actual = endpoint(root, "helper-C-E", 2)
    assert max(abs(float(x)) for x in actual - O - camera * p["E"]) < 4e-6
    assert max(abs(float(x)) for x in endpoint(root, "helper-B-E", 2) - actual) < 1e-6


@pytest.mark.parametrize(
    "replacements", ([(r"\frac{1}{9}", "0")], [(r"\frac{1}{9}", r"-\frac{1}{4}")])
)
def test_changed_flat_triangle_has_the_true_right_or_obtuse_angle(replacements):
    original = next(c for c in CASES if c["task"] == "505387")
    case = changed(original, replacements)
    p, _ = geometry(read(case))
    (spec,) = get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(case["context"])
    root = ET.fromstring(spec["svg_text"])
    B, M = endpoint(root, "triangle-B-M", 1), endpoint(root, "triangle-B-M", 2)
    N = endpoint(root, "triangle-M-N", 2)
    expected = float(
        (p["B"] - p["M"]).dot(p["N"] - p["M"])
        / ((p["B"] - p["M"]).norm() * (p["N"] - p["M"]).norm())
    )
    actual = float((B - M).dot(N - M) / ((B - M).norm() * (N - M).norm()))
    assert abs(actual - expected) < 1e-7 and actual < 1e-7
