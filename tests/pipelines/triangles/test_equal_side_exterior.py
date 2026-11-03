"""Verify the exterior-bisector extension of the common equal-side runner."""

import math
import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from equal_side_cases import GROUPS, parent_html, plan, section
from test_altitude_quad_preparation import angle
from test_equal_side_preparation import FRAMES, check_rows, synthetic
from test_two_ray_frozen_lifecycle import OfflineGateway
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.triangles.general.equal_side_figures import (
    EXTENSION,
    EXTERIOR,
    selection,
    source_bytes,
)


@pytest.mark.parametrize("frame", FRAMES)
@pytest.mark.parametrize(
    "values", [(30, 86), (60, 30), (100, 20), (150, 10), (20, 150), (59, 88)]
)
def test_both_external_intersections_all_vertex_frames_and_angle_equations(
    frame, values
):
    case, ctx = synthetic("exterior", frame, values)
    model = selection(ctx)[0]
    result = plan(case, ctx)
    assert result.answer == str(abs(values[1] - values[0]))
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("frame", FRAMES)
def test_opposite_ray_svg_has_actual_lengths_collinearity_and_angle_halves(frame):
    _, ctx = synthetic("exterior", frame, (60, 30))
    root = ET.fromstring(selection(ctx)[-1]["svg_text"])
    ids = [e.get("id") for e in root.iter() if e.get("id")]
    assert len(ids) == len(set(ids))
    elements = {e.get("id"): e for e in root if e.get("id")}

    def ends(name):
        item = elements[name]
        return [
            tuple(float(item.get(axis + str(i))) for axis in ["x", "y"]) for i in [1, 2]
        ]

    a, b = ends("AB")
    _, c = ends("BC")
    _, d = ends("CD")
    _, e = ends("AE")
    points = dict(zip("ABCDE", [a, b, c, d, e]))
    assert d[0] < a[0] < b[0] and abs(d[1] - a[1]) < 1e-5
    assert abs(math.dist(c, b) - math.dist(c, e)) < 1e-5
    assert abs(angle(points, "BCD") - angle(points, "DCE")) < 1e-4
    assert abs(angle(points, "BDC") - angle(points, "CDE")) < 1e-4
    assert abs(angle(points, "BDE") - 30) < 1e-4
    assert abs(angle(points, "ACE") - 180) < 1e-4
    assert elements["CD"].get("stroke") == "#143B8F"
    assert {"equal-CB", "equal-CE", *("label-" + n for n in "ABCDE")} <= elements.keys()


@pytest.mark.parametrize("values", [(0, 86), (30, 0), (30, 30), (100, 80), (120, 90)])
def test_parallel_external_bisector_or_degenerate_triangle_is_rejected(values):
    case, ctx = synthetic("exterior", values=values)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "old,new",
    [
        ("CD — биссектриса внешнего", "AD — биссектриса внешнего"),
        ("вершине C", "вершине A"),
        ("прямой AB", "прямой AC"),
        ("стороны AC", "стороны BC"),
        ("за точку C", "за точку A"),
        ("CE = CB", "CE = AB"),
        ("угол BDE", "угол CDE"),
        ("CD — биссектриса внешнего угла", "CD — биссектриса угла"),
    ],
)
def test_unknown_side_extensions_bisector_roles_or_target_rays_fail_closed(old, new):
    case, ctx = synthetic("exterior")
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        old, new
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "values,frame,lost",
    [
        ((30, 86), "ABC", False),
        ((30, 86), "CAB", False),
        ((60, 30), "ABC", False),
        ((60, 30), "CAB", False),
        ((60, 30), "CAB", True),
    ],
)
def test_local_frozen_roundtrip_preserves_both_ray_styles_and_checks_condition_readback(
    values, frame, lost
):
    case, ctx = synthetic("exterior", frame, values)
    gateway = OfflineGateway({**case, "context": ctx}, omit_condition_write=lost)
    rule = GROUPS["27777"]["rule"]
    kwargs = {"parent_solution_html": parent_html("27777")}
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": case["task"]},
        EXTERIOR,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared" and not gateway.uploads and not gateway.writes
    result = _apply_record(gateway, record, EXTERIOR, rule, **kwargs)
    assert result["status"] == ("failed" if lost else "applied"), result
    assert len(gateway.uploads) == int(frame != "ABC" or values[0] > values[1])
    if not lost:
        assert (
            _apply_record(gateway, record, EXTERIOR, rule, **kwargs)["status"]
            == "already_complete"
        )


@pytest.mark.parametrize(
    "values,expected", [(("30{,}5", 86), "55,5"), (("60{,}5", 30), "30,5")]
)
def test_exact_half_degrees_in_both_directions(values, expected):
    case, ctx = synthetic("exterior", values=values)
    model = selection(ctx)[0]
    result = plan(case, ctx)
    assert result.answer == expected
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], model)


@pytest.mark.parametrize(
    "values",
    [
        ("30{,}00000000000000001", 30),
        ("179{,}99999999999999999", "0{,}000000000000000001"),
    ],
)
def test_unrepresentable_opposite_ray_diagrams_are_rejected(values):
    case, ctx = synthetic("exterior", values=values)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("change", ["source", "reference", "extra"])
def test_changed_source_cannot_supply_the_external_bisector_construction(change):
    case, ctx = synthetic("exterior")
    asset = ctx["normalized_content"]["assets"][0]
    if change == "source":
        asset["asset_id"] = EXTENSION
        asset["url"] = "/assets/" + EXTENSION
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            EXTERIOR, EXTENSION
        )
    elif change == "reference":
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            EXTERIOR, "unknown"
        )
    else:
        ctx["normalized_content"]["assets"].append(deepcopy(asset))
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_new_source_is_packaged_and_hash_pinned():
    assert source_bytes(EXTERIOR).lstrip().startswith((b"<?xml", b"<svg"))


@pytest.mark.parametrize("change", ["facts", "segments"])
def test_equivalent_angle_order_and_equal_segment_orientations(change):
    case, ctx = synthetic("exterior")
    condition = section(ctx, "condition")
    if change == "facts":
        condition["html"] = condition["html"].replace(
            "угол A равен 30°, угол B равен 86°", "угол B равен 86°, угол A равен 30°"
        )
    else:
        condition["html"] = (
            condition["html"]
            .replace("прямой AB", "прямой BA")
            .replace("CE = CB", "BC = EC")
            .replace("угол BDE", "угол EDB")
        )
    assert plan(case, ctx).answer == "56"
