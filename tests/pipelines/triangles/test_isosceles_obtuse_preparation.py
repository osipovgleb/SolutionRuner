"""Exercise public obtuse preparation, immutable conditions and frozen readback."""

from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from isosceles_obtuse_cases import CASES, GROUPS, parent_html, plan, section
from test_isosceles_obtuse_proofs import check_rows
from test_two_ray_frozen_lifecycle import OfflineGateway
from test_two_ray_source_methods import replay

from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.triangles.isosceles.obtuse_figures import (
    KEY,
    SOURCE,
    selection,
)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_public_answers_methods_bindings_and_replay(case):
    before = deepcopy(case["context"])
    ctx = deepcopy(before)
    for key in ("answer", "solution"):
        section(ctx, key)["html"] = "<p>Не использовать: 999.</p>"
    untouched = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == untouched
    expected = sp.Rational(
        BeautifulSoup(section(before, "answer")["html"], "html.parser")
        .get_text()
        .replace(",", ".")
    )
    assert sp.Rational(result.answer.replace(",", ".")) == expected
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], selection(ctx)[0])
    assert plan(case, ctx).transformations == ()
    old, new = (
        BeautifulSoup(section(c, "condition")["html"], "html.parser")
        for c in (before, ctx)
    )
    for soup in (old, new):
        assert len(soup.find_all("img")) == 1
        soup.img.decompose()
    assert str(old) == str(new)
    assert len(ctx["normalized_content"]["assets"]) == 1
    assert ctx["normalized_content"]["assets"][0]["asset_key"] == KEY
    profile = get_group_profile(case["group"])
    handler = get_handler(profile.content_rule_key)
    assert profile.existing_solution_policy == "rewrite"
    assert profile.source_group_id == GROUPS[case["group"]]["group_uuid"]
    assert handler.requires_frozen_manifest and handler.verify_content_readback


@pytest.mark.parametrize("group", list(GROUPS))
def test_parent_methods_or_assets_cannot_change(group):
    case = next(c for c in CASES if c["task"] == group)
    with pytest.raises(ContentPlanError):
        plan(case, parent=parent_html(group) + "<p>Другой метод.</p>")
    with pytest.raises(ContentPlanError):
        get_handler(GROUPS[group]["rule"]).plan(
            PlanInput(
                case["context"],
                parent_asset_id="other",
                parent_solution_html=parent_html(group),
            )
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unknown_instructions_fail_closed(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Удвойте ответ.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "task", ["34209", "19639", "34251", "34311", "34353", "34413", "34463", "34515"]
)
def test_offline_frozen_preview_uuid_and_authoritative_readback(task):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case)
    rule = GROUPS[case["group"]]["rule"]
    kwargs = {"parent_solution_html": parent_html(case["group"])}
    record = _prepared_record(
        gateway,
        {"problem_id": case["context"]["problem_id"], "source_problem_id": task},
        SOURCE,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    assert _apply_record(gateway, record, SOURCE, rule, **kwargs)["status"] == "applied"
    assert len(gateway.uploads) == len(gateway.writes) == 1
    assert (
        _apply_record(gateway, record, SOURCE, rule, **kwargs)["status"]
        == "already_complete"
    )


@pytest.mark.parametrize("task", ["34209", "19639"])
def test_lost_condition_write_fails_offline_readback(task):
    case = next(c for c in CASES if c["task"] == task)
    gateway = OfflineGateway(case, omit_condition_write=True)
    rule = GROUPS[case["group"]]["rule"]
    kwargs = {"parent_solution_html": parent_html(case["group"])}
    record = _prepared_record(
        gateway,
        {"problem_id": case["context"]["problem_id"], "source_problem_id": task},
        SOURCE,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared"
    assert _apply_record(gateway, record, SOURCE, rule, **kwargs)["status"] == "failed"


def test_unrelated_asset_cannot_be_silently_deleted():
    case = CASES[0]
    ctx = deepcopy(case["context"])
    ctx["normalized_content"]["assets"].append(
        {"asset_key": "image_2", "asset_id": "other"}
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_generated_diagram_checksum_must_match():
    case = CASES[0]
    with pytest.raises(ContentPlanError):
        get_handler(GROUPS[case["group"]]["rule"]).plan(
            PlanInput(
                case["context"],
                parent_asset_id=SOURCE,
                parent_solution_html=parent_html(case["group"]),
                generated_solution_assets=(
                    {
                        "asset_key": KEY,
                        "source_asset_id": "preview-bad",
                        "url": "/assets/preview-bad",
                        "sha256": "0" * 64,
                    },
                ),
            )
        )
