"""Changed numeric scenes must project independent 3D geometry and exact labels."""

import hashlib
import math
import xml.etree.ElementTree as ET

import pytest
import sympy as sp
from midpoint_projection_equations import verify
from midpoint_projection_geometry import geometry
from midpoint_projection_source_cases import CASES, GROUPS, changed, plan, read
from midpoint_source_cases import replay, solution_html
from test_line_projection_generated import endpoint
from test_pyramid_midsections_lifecycle import without_figures

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids import projection_drawing

NS = "{http://www.w3.org/2000/svg}"
SAMPLES = [
    (
        "507611",
        [("AA_1 = 4", "AA_1 = 7"), ("C_1D_1 = 6", "C_1D_1 = 3")],
        ["3", "6", "7"],
    ),
    ("507611", [("A_1D_1 = 6", r"A_1D_1 = \sqrt{7}")], ["4", "6", "√7"]),
    ("507615", [("AB = 4", "AB = 10"), ("CC_1 = 4", "CC_1 = 2,5")], ["10", "5/2", "6"]),
    ("507615", [("BC = 6", r"BC = \sqrt{5}")], ["4", "4", "√5"]),
    (
        "525393",
        [(r"\sqrt{17}", "5"), (r"\sqrt{29}", "7"), (r"2\sqrt{5}", "6")],
        ["3", "3", "5", "7"],
    ),
    (
        "525393",
        [(r"\sqrt{17}", "4"), (r"\sqrt{29}", "5"), (r"2\sqrt{5}", "4")],
        ["2", "2", "4", "5"],
    ),
]


def prepared(task, replacements, missing=False):
    case = next(c for c in CASES if c["task"] == task)
    ctx = changed(case, replacements, without_figures(case) if missing else None)
    (spec,) = get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx)
    return case, ctx, spec


@pytest.mark.parametrize("task,replacements,labels", SAMPLES)
@pytest.mark.parametrize("missing", (False, True))
def test_generated_plan_equations_exact_labels_hash_and_idempotency(
    task, replacements, labels, missing
):
    case, ctx, spec = prepared(task, replacements, missing)
    result = plan(case, ctx)
    verify(read(ctx), solution_html(result))
    assert spec["sha256"] == hashlib.sha256(spec["svg_text"].encode()).hexdigest()
    root = ET.fromstring(spec["svg_text"])
    assert sorted(e.text for e in root.findall(NS + "text")) == sorted(labels)
    ids = [e.get("id") for e in root.iter() if e.get("id")]
    assert len(ids) == len(set(ids))
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations
    assert len(ctx["normalized_content"]["assets"]) == 1
    with pytest.raises(ContentPlanError):
        plan(case, changed(case, replacements), generated_solution_assets=())


def _marker(root, camera, p, origin, normal, first, second):
    u, v = p[first] - p[normal], p[second] - p[normal]
    assert sp.simplify(u.dot(v)) == 0
    frame = camera * sp.Matrix.hstack(u / u.norm(), v / v.norm())
    base = origin + camera * p[normal]
    marker = [
        endpoint(root, "right-angle-0", 1),
        endpoint(root, "right-angle-0", 2),
        endpoint(root, "right-angle-1", 2),
    ]
    recovered = [frame.inv() * (q - base) for q in marker]
    assert abs(float(recovered[0][1])) < 1e-5
    assert abs(float(recovered[2][0])) < 1e-5
    assert math.isclose(float(recovered[0][0]), float(recovered[1][0]), abs_tol=1e-5)
    assert math.isclose(float(recovered[2][1]), float(recovered[1][1]), abs_tol=1e-5)
    assert float(recovered[0][0]) > 0 and float(recovered[2][1]) > 0


@pytest.mark.parametrize("task,replacements,labels", SAMPLES)
def test_scene_points_and_right_angle_marker_follow_independent_geometry(
    task, replacements, labels
):
    _, ctx, spec = prepared(task, replacements)
    m = read(ctx)
    p, _ = geometry(m)
    root = ET.fromstring(spec["svg_text"])
    if task.startswith("507"):
        O = endpoint(root, "wire-A-B", 1)
        B = endpoint(root, "wire-A-B", 2)
        D = endpoint(root, "wire-A-D", 2)
        A1 = endpoint(root, "wire-A-A_1", 2)
        camera = sp.Matrix.hstack(
            (B - O) / p["B"][0], (D - O) / p["D"][1], (A1 - O) / p["A_1"][2]
        )
        for i, name in enumerate("EF", 1):
            actual = endpoint(root, "midpoint-E-F", i)
            assert max(abs(float(x)) for x in actual - O - camera * p[name]) < 4e-6
        assert root.find(NS + "polygon") is None
        target = "B" if task == "507611" else "A_1"
        _marker(root, camera, p, O, target, "E", "F")
    else:
        B = endpoint(root, "edge-B-C", 1)
        C = endpoint(root, "edge-B-C", 2)
        S = endpoint(root, "edge-S-A", 1)
        A = endpoint(root, "edge-S-A", 2)
        O = (B + C) / 2
        X = (C - B) / (p["C"] - p["B"]).norm()
        Y = (S - O) / p["S"][1]
        Z = (A - O - p["A"][1] * Y) / p["A"][2]
        camera = sp.Matrix.hstack(X, Y, Z)
        actual = endpoint(root, "edge-A-M", 2)
        assert max(abs(float(x)) for x in actual - O - camera * p["M"]) < 4e-6
        _marker(root, camera, p, O, "M", "A", "S")


@pytest.mark.parametrize("task,replacements,labels", SAMPLES)
def test_generated_hash_is_required_before_content_plan(task, replacements, labels):
    case, ctx, spec = prepared(task, replacements)
    wrong = {
        "asset_key": spec["asset_key"],
        "sha256": "0" * 64,
        "source_asset_id": "wrong",
        "url": "/assets/wrong",
    }
    with pytest.raises(ContentPlanError):
        plan(case, ctx, generated_solution_assets=(wrong,))


def test_template_tampering_refuses(monkeypatch):
    monkeypatch.setattr(projection_drawing, "TEMPLATE_SHA256", "0" * 64)
    with pytest.raises(ContentPlanError):
        projection_drawing.template("box_midpoint_side")
