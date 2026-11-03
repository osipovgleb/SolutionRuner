"""Public side-altitude plans preserve mathematics, asset roles and frozen replay."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from isosceles_altitude_cases import CASES, GROUPS, PARENTS, parent_html, plan, section
from test_isosceles_side_altitude_model import PARAMETERS, projection_geometry
from test_isosceles_side_altitude_proofs import verify_rows
from test_two_ray_frozen_lifecycle import OfflineGateway
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
    _solution_assets,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.triangles.isosceles.side_altitude_model import (
    read_context,
)


def html(result):
    return next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_each_public_plan_matches_independent_projection_and_parent_methods(case):
    result = plan(case)
    m = read_context(case["context"])
    oracle = projection_geometry(*PARAMETERS[case["task"]])
    verify_rows(html(result), m, oracle)
    assert float(result.answer.replace(",", ".")) == pytest.approx(
        float(oracle[m.requested_kind])
    )
    p = get_group_profile(case["group"])
    handler = get_handler(p.content_rule_key)
    assert (
        p.existing_solution_policy == "rewrite"
        and p.source_group_id == GROUPS[case["group"]]["group_uuid"]
    )
    assert handler.requires_frozen_manifest and handler.verify_content_readback
    assert not BeautifulSoup(html(result), "html.parser").find("img")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_input_is_immutable_old_answers_unused_condition_words_preserved_and_replay_empty(
    case,
):
    ctx = deepcopy(case["context"])
    for key in ["solution", "answer"]:
        section(ctx, key)["html"] = "<p>Не использовать: 999.</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == plan(case).answer
    replay(ctx, result.transformations)
    assert len(ctx["normalized_content"]["assets"]) == 1
    assert plan(case, ctx).transformations == ()
    old = BeautifulSoup(section(before, "condition")["html"], "html.parser")
    new = BeautifulSoup(section(ctx, "condition")["html"], "html.parser")
    for soup in (old, new):
        for image in soup.find_all("img"):
            image.decompose()
    assert str(old) == str(new)
    assert (
        len(
            BeautifulSoup(section(ctx, "condition")["html"], "html.parser").find_all(
                "img"
            )
        )
        == 1
    )


@pytest.mark.parametrize(
    "task", ["27320", "4837", "4839", "517192", "517230", "33635", "19309", "19353"]
)
def test_offline_frozen_roundtrip_replaces_preview_ids_and_checks_parent_readback(task):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case)
    parent = PARENTS[case["group"]]["context"]
    source = next(
        a["asset_id"]
        for a in parent["normalized_content"]["assets"]
        if a["asset_key"] == "image_1"
    )
    rule = GROUPS[case["group"]]["rule"]
    kwargs = {
        "parent_solution_html": parent_html(case["group"]),
        "parent_solution_assets": _solution_assets(parent),
    }
    record = _prepared_record(
        gateway,
        {"problem_id": case["context"]["problem_id"], "source_problem_id": task},
        source,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    result = _apply_record(gateway, record, source, rule, **kwargs)
    assert result["status"] == "applied", result
    assert len(gateway.context["normalized_content"]["assets"]) == 1
    assert (
        _apply_record(gateway, record, source, rule, **kwargs)["status"]
        == "already_complete"
    )
    assert len(gateway.writes) == 1


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_extra_instructions_are_not_silently_dropped(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Удвойте ответ.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", list(GROUPS))
def test_changed_parent_methods_block_public_preparation(group):
    case = next(c for c in CASES if c["task"] == group)
    with pytest.raises(ContentPlanError):
        plan(case, parent=parent_html(group) + "<p>Еще один способ.</p>")


def test_incorrect_generated_checksum_blocks_the_plan():
    case = next(c for c in CASES if c["task"] == "27320")
    parent = PARENTS[case["group"]]["context"]
    source = next(
        a["asset_id"]
        for a in parent["normalized_content"]["assets"]
        if a["asset_key"] == "image_1"
    )
    generated = (
        {
            "asset_key": "side_altitude_7882a0e2",
            "source_asset_id": "preview-bad",
            "url": "/assets/preview-bad",
            "sha256": "0" * 64,
        },
    )
    with pytest.raises(ContentPlanError):
        get_handler(GROUPS[case["group"]]["rule"]).plan(
            PlanInput(
                case["context"],
                parent_asset_id=source,
                parent_solution_html=parent_html(case["group"]),
                generated_solution_assets=generated,
            )
        )


def test_unrelated_figure_cannot_be_removed_as_a_legacy_note():
    case = next(c for c in CASES if c["task"] == "27320")
    ctx = deepcopy(case["context"])
    ctx["normalized_content"]["assets"].append(
        {
            "asset_key": "editorial_figure",
            "asset_id": "human-figure",
            "kind": "ordinary_image",
            "url": "/assets/human-figure",
        }
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_parent_note_metadata_must_match_the_reviewed_source():
    case = next(c for c in CASES if c["task"] == "27327")
    parent = PARENTS[case["group"]]["context"]
    source = next(
        a["asset_id"]
        for a in parent["normalized_content"]["assets"]
        if a["asset_key"] == "image_1"
    )
    with pytest.raises(ContentPlanError):
        get_handler(GROUPS[case["group"]]["rule"]).plan(
            PlanInput(
                case["context"],
                parent_asset_id=source,
                parent_solution_html=parent_html(case["group"]),
                parent_solution_assets=(),
            )
        )


@pytest.mark.parametrize("task", ["27320", "517192"])
def test_missing_condition_write_fails_authoritative_offline_readback(task):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case, omit_condition_write=True)
    parent = PARENTS[case["group"]]["context"]
    source = next(
        a["asset_id"]
        for a in parent["normalized_content"]["assets"]
        if a["asset_key"] == "image_1"
    )
    rule = GROUPS[case["group"]]["rule"]
    kwargs = {
        "parent_solution_html": parent_html(case["group"]),
        "parent_solution_assets": _solution_assets(parent),
    }
    record = _prepared_record(
        gateway,
        {"problem_id": case["context"]["problem_id"], "source_problem_id": task},
        source,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared"
    assert _apply_record(gateway, record, source, rule, **kwargs)["status"] == "failed"
