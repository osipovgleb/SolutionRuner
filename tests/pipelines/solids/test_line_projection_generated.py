"""Changed dimensions require actual geometry, labels and deterministic local assets."""

import hashlib
import itertools
import math
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
import sympy as sp
from line_projection_equation_oracle import verify
from line_projection_source_cases import CASES, GROUPS, changed_measurements, plan, read
from midpoint_source_cases import replay, section, solution_html
from test_pyramid_midsections_lifecycle import without_figures

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids import projection_drawing

SAMPLES = [
    ("507576", (3, 5, 7)),
    ("507576", (8, 12, 6)),
    ("507703", (3, 5, 7)),
    ("511478", (9, 9, 6)),
    ("513098", (6, 4, 5)),
    ("513098", (3, 7, 4)),
]
NS = "{http://www.w3.org/2000/svg}"


def prepared(task, dimensions, missing=False):
    case = next(c for c in CASES if c["task"] == task)
    ctx = changed_measurements(
        case, dimensions, without_figures(case) if missing else None
    )
    specs = get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx)
    assert len(specs) == 1
    return case, ctx, specs[0]


@pytest.mark.parametrize("task,dims", SAMPLES)
@pytest.mark.parametrize("missing", (False, True))
def test_changed_dimensions_full_plan_equations_and_idempotent_generated_asset(
    task, dims, missing
):
    case, ctx, spec = prepared(task, dims, missing)
    before = deepcopy(ctx)
    result = plan(case, ctx)
    verify(solution_html(result), read(ctx))
    assert ctx == before
    assert spec["sha256"] == hashlib.sha256(spec["svg_text"].encode()).hexdigest()
    root = ET.fromstring(spec["svg_text"])
    labels = {e.get("id"): e.text for e in root.findall(NS + "text")}
    assert labels["length-0"] == str(dims[0]) and labels["length-1"] == str(dims[1])
    if task != "513098":
        assert labels["length-2"] == str(dims[2])
    else:
        assert labels["length-2"] == ("√61" if dims == (6, 4, 5) else "5")
    replay(ctx, result.transformations)
    assert len(ctx["normalized_content"]["assets"]) == 1
    assert (
        ctx["normalized_content"]["assets"][0]["asset_key"] == "box_distance_solution"
    )
    assert not plan(case, ctx).transformations
    assert section(ctx, "condition") == section(before, "condition")


@pytest.mark.parametrize("task,dims", SAMPLES)
def test_wrong_generated_hash_is_rejected_before_any_content_plan(task, dims):
    case, ctx, spec = prepared(task, dims)
    asset = {
        "asset_key": spec["asset_key"],
        "sha256": "0" * 64,
        "source_asset_id": "wrong",
        "url": "/assets/wrong",
    }
    with pytest.raises(ContentPlanError):
        plan(case, ctx, generated_solution_assets=(asset,))
    with pytest.raises(ContentPlanError):
        plan(case, ctx, generated_solution_assets=())


def endpoint(root, identifier, suffix):
    node = root.find(f"{NS}line[@id='{identifier}']")
    assert node is not None, identifier
    return sp.Matrix([float(node.get(axis + str(suffix))) for axis in "xy"])


@pytest.mark.parametrize("task,dims", SAMPLES[:4])
def test_svg_foot_and_right_angle_are_the_projection_of_independent_3d_points(
    task, dims
):
    from plane_geometry_oracle import foot
    from test_line_projection_models import coordinates

    _, _, spec = prepared(task, dims)
    root = ET.fromstring(spec["svg_text"])
    a, b, h = map(sp.Integer, dims)
    p = coordinates(a, b, h)
    O = endpoint(root, "wire-A-B", 1)
    X = endpoint(root, "wire-A-B", 2)
    D = endpoint(root, "wire-A-D", 2)
    Z = endpoint(root, "wire-A-A_1", 2)
    camera = sp.Matrix.hstack((X - O) / a, (D - O) / b, (Z - O) / h)
    face = task == "507576"
    H = foot(p["C_1"], p["C"], p["D_1"]) if face else foot(p["B"], p["A"], p["C"])
    actual = endpoint(root, "projection-" + ("C_1" if face else "B") + "-H", 2)
    assert max(abs(float(x)) for x in actual - O - camera * H) < 3e-6
    first, second = ("C", "C_1") if face else ("A", "B")
    u, v = p[first] - H, p[second] - H
    assert sp.simplify(u.dot(v)) == 0
    # Recover each marker in its actual 3D section; perspective need not preserve a right angle.
    unit_u, unit_v = u / u.norm(), v / v.norm()
    frame = camera * sp.Matrix.hstack(unit_u, unit_v)
    marker = [
        endpoint(root, "right-angle-0", 1),
        endpoint(root, "right-angle-0", 2),
        endpoint(root, "right-angle-1", 2),
    ]
    recovered = [frame.inv() * (q - actual) for q in marker]
    assert abs(float(recovered[0][1])) < 1e-5
    assert abs(float(recovered[2][0])) < 1e-5
    assert math.isclose(float(recovered[0][0]), float(recovered[1][0]), abs_tol=1e-5)
    assert math.isclose(float(recovered[2][1]), float(recovered[1][1]), abs_tol=1e-5)
    assert float(recovered[0][0]) > 0 and float(recovered[2][1]) > 0


def test_changed_template_hash_fails_closed(monkeypatch):
    monkeypatch.setattr(projection_drawing, "TEMPLATE_SHA256", "0" * 64)
    with pytest.raises(ContentPlanError):
        projection_drawing.template("pyramid")


@pytest.mark.parametrize("task,dims", SAMPLES)
def test_generated_figures_freeze_and_complete_readback_in_local_fake_gateway(
    task, dims
):
    from test_line_projection_lifecycle import apply_offline
    from test_line_projection_lifecycle import prepared as freeze
    from test_midpoint_area_lifecycle import OfflineGateway

    case, ctx, _ = prepared(task, dims)
    changed = {**case, "context": ctx}
    gateway = OfflineGateway(changed)
    record = freeze(changed, gateway)
    assert record["status"] == "prepared", record
    assert len(record["generated_diagrams"]) == 1
    assert not gateway.uploads and not gateway.writes
    result = apply_offline(changed, gateway, record)
    assert result["status"] == "applied", result
    assert len(gateway.uploads) == len(gateway.writes) == 1
    assert apply_offline(changed, gateway, record)["status"] == "already_complete"
    assert len(gateway.uploads) == len(gateway.writes) == 1


@pytest.mark.parametrize("dims", ((6, 4, 5), (3, 7, 4)))
def test_pyramid_arc_is_a_projected_3d_circle_with_the_actual_line_to_plane_angle(dims):
    _, _, spec = prepared("513098", dims)
    root = ET.fromstring(spec["svg_text"])
    a, b, h = map(sp.Integer, dims)
    O = endpoint(root, "edge-A-B", 1)
    B = endpoint(root, "edge-A-B", 2)
    D = endpoint(root, "edge-D-A", 1)
    S = endpoint(root, "edge-S-A", 1)
    camera = sp.Matrix.hstack((B - O) / a, (D - O) / b, (S - O) / h)
    u = sp.Matrix([a, 0, -h])
    v = sp.Matrix([a, b, -h])
    u = u / u.norm()
    v = v / v.norm()
    cosine = sp.simplify(u.dot(v))
    w = (v - cosine * u) / sp.sqrt(1 - cosine * cosine)
    frame = camera * sp.Matrix.hstack(u, w)
    node = root.find(f"{NS}polyline[@id='projection-angle']")
    assert node is not None
    screen_points = [
        sp.Matrix([float(x) for x in p.split(",")]) for p in node.get("points").split()
    ]
    recovered = [frame.inv() * (p - S) for p in screen_points]
    radii = [float(p.norm()) for p in recovered]
    assert max(radii) - min(radii) < 3e-6
    angles = [math.atan2(float(p[1]), float(p[0])) for p in recovered]
    assert abs(angles[0]) < 1e-6
    assert math.isclose(
        angles[-1], math.atan(float(b / sp.sqrt(a * a + h * h))), abs_tol=1e-6
    )
    assert all(x < y for x, y in itertools.pairwise(angles))
