"""Verify registered native preparations, source retention and complete parent pins."""

from copy import deepcopy

import pytest
from midpoint_source_cases import replay, section
from orthogonal_element_cases import BOUND, GROUPS, PENDING, model, plan
from orthogonal_element_oracle import verify

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import all_group_profiles
from solution_runner.pipelines.solids.orthogonal_element_figures import diagram_specs


@pytest.mark.parametrize("case", BOUND, ids=lambda c: c["task"])
def test_complete_native_plan_keeps_condition_source_and_corrects_answer(case):
    ctx = deepcopy(case["context"])
    snapshot = deepcopy(ctx)
    section(ctx, "answer")["html"] = "<p>999</p>"
    result = plan(case, ctx)
    assert result.answer != "999"
    assert section(ctx, "condition") == section(snapshot, "condition")
    assert section(ctx, "source") == section(snapshot, "source")
    assert (
        ctx["normalized_content"]["assets"] == snapshot["normalized_content"]["assets"]
    )
    assert not any(
        t["transformation_target_id"].startswith(
            ("section:condition", "section:source", "asset:image_1")
        )
        for t in result.transformations
    )
    prepared = deepcopy(ctx)
    replay(prepared, result.transformations)
    assert section(prepared, "condition") == section(snapshot, "condition")
    assert section(prepared, "source") == section(snapshot, "source")
    verify(model(case), section(prepared, "solution")["html"])


@pytest.mark.parametrize("case", PENDING, ids=lambda c: c["task"])
def test_incomplete_numeric_png_fails_before_any_preparation(case):
    with pytest.raises(ContentPlanError, match="PNG"):
        plan(case)


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize(
    "override",
    [
        {"parent_asset_id": "foreign"},
        {"parent_solution_html": "<p>Другое решение.</p>"},
        {"parent_solution_assets": ()},
    ],
)
def test_complete_parent_method_and_figure_list_are_required(group, override):
    case = next(c for c in BOUND if c["task"] == group)
    with pytest.raises(ContentPlanError):
        plan(case, **override)


@pytest.mark.parametrize("group", GROUPS)
def test_profiles_use_actual_catalog_theme_and_listing_index(group):
    p = all_group_profiles()[group]
    assert p.content_rule_key == GROUPS[group]["rule"]
    assert p.snapshot_theme_id == "a81d395d-689f-4f3b-b76b-9aa4d872d267"
    assert p.group_order_index == GROUPS[group]["order_index"]


@pytest.mark.parametrize("group", GROUPS)
def test_missing_own_condition_cannot_substitute_parent_numbers(group):
    case = next(c for c in BOUND if c["task"] == group)
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = "<p>Условие без рисунка.</p>"
    section(ctx, "condition")["asset_keys"] = []
    ctx["normalized_content"]["assets"] = [
        a for a in ctx["normalized_content"]["assets"] if a["asset_key"] != "image_1"
    ]
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_numerically_different_native_solution_figure_is_rejected():
    case = BOUND[0]
    ctx = deepcopy(case["context"])
    old = next(
        a for a in ctx["normalized_content"]["assets"] if a["asset_key"] == "image_2"
    )
    previous = old["asset_id"]
    old.update(asset_id="foreign", url="/assets/foreign")
    section(ctx, "solution")["html"] = section(ctx, "solution")["html"].replace(
        previous, "foreign"
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_only_missing_solution_diagrams_are_generated():
    generated = [c["task"] for c in BOUND if diagram_specs(c["context"])]
    assert set(generated) == {
        "274955",
        "275871",
        "276371",
        "276871",
        "278371",
        "278871",
        "279371",
        "280871",
        "281371",
    }
