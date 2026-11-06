"""Preparation freezes native and generated figures without uploads or task writes."""

from copy import deepcopy

import pytest
from midpoint_projection_source_cases import (
    CASES,
    GROUPS,
    arguments,
    changed,
    plan,
    read,
)
from test_midpoint_area_lifecycle import OfflineGateway
from test_midpoint_projection_figures import SAMPLES

from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.spatial_distance_sources import compatible


def freeze(case, context):
    gateway = OfflineGateway({**case, "context": context})
    record = _prepared_record(
        gateway,
        {"problem_id": context["problem_id"], "source_problem_id": case["task"]},
        content_rule_key=GROUPS[case["group"]]["rule"],
        **arguments(case["group"]),
    )
    assert not gateway.writes and not gateway.uploads
    return record


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_records_prepare_without_any_write(case):
    record = freeze(case, case["context"])
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == plan(case).answer
    assert not record["generated_diagrams"]


@pytest.mark.parametrize("task,replacements,labels", SAMPLES)
def test_actual_changed_figure_is_frozen_without_upload(task, replacements, labels):
    case = next(c for c in CASES if c["task"] == task)
    ctx = changed(case, replacements)
    record = freeze(case, ctx)
    assert record["status"] == "prepared", record
    assert len(record["generated_diagrams"]) == 1
    assert record["expected_answer"] == plan(case, ctx).answer


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unreviewed_image_refuses_before_preparation(case):
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    old = asset["asset_id"]
    asset["asset_id"] = "00000000-0000-4000-8000-000000000001"
    for s in ctx["normalized_content"]["sections"]:
        s["html"] = s["html"].replace(old, asset["asset_id"])
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    assert freeze(case, ctx)["status"] in {"blocked", "failed"}


def test_square_scene_cannot_silently_replace_the_perpendicular_plane_claim():
    square = read(next(c["context"] for c in CASES if c["task"] == "511324"))
    parent = read(next(c["context"] for c in CASES if c["task"] == "485934"))
    square_source = "8a9c6676-fa04-4271-a557-ccf630c55a82"
    triangle_source = "8dac3233-9ae3-430c-831b-d3d74edc87eb"
    assert compatible(square, square_source, "solution", "image_1")
    assert not compatible(parent, square_source, "solution", "image_1")
    assert compatible(parent, triangle_source, "solution", "image_1")
    assert not compatible(square, triangle_source, "solution", "image_1")


def test_tetrahedron_original_numerals_are_only_reused_with_their_actual_edges():
    parent = read(next(c["context"] for c in CASES if c["task"] == "525393"))
    child = read(next(c["context"] for c in CASES if c["task"] == "526014"))
    first = "c7e3fb7d-1da4-4bf1-b096-fd89329cc2c3"
    second = "ecaddbc3-35b7-45ef-bf85-72041a64a307"
    assert compatible(parent, first, "solution", "image_1")
    assert compatible(child, second, "solution", "image_1")
    assert not compatible(parent, second, "solution", "image_1")
    assert not compatible(child, first, "solution", "image_1")


@pytest.mark.parametrize("task", ("507611", "507615"))
def test_box_scene_requires_both_its_midpoint_role_and_actual_dimensions(task):
    case = next(c for c in CASES if c["task"] == task)
    source = case["context"]["normalized_content"]["assets"][0]["asset_id"]
    m = read(case["context"])
    assert compatible(m, source, "solution", "image_1")
    replacement = (
        [("AA_1 = 4", "AA_1 = 7")] if task == "507611" else [("CC_1 = 4", "CC_1 = 7")]
    )
    assert not compatible(
        read(changed(case, replacement)), source, "solution", "image_1"
    )
    other = read(
        next(
            c["context"]
            for c in CASES
            if c["task"] == ("507615" if task == "507611" else "507611")
        )
    )
    assert not compatible(other, source, "solution", "image_1")


def test_rectangle_with_external_altitude_does_not_reuse_the_interior_foot_scene():
    case = next(c for c in CASES if c["task"] == "526216")
    ctx = changed(case, [("SC=5", r"SC=\sqrt{13}")])
    assert read(ctx).q["foot"] > 1
    assert not compatible(
        read(ctx), "b86e89a7-5294-4ba2-8c9c-792773074ed8", "solution", "image_1"
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
