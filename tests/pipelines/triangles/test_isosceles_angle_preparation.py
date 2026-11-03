"""Public angle plans preserve conditions, reject ambiguity and survive frozen replay."""

from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from isosceles_angle_cases import CASES, GROUPS, PARENTS, parent_html, plan, section
from test_isosceles_angle_model import check_rows
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
from solution_runner.pipelines.triangles.isosceles.angle_figures import KEY, selection


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_public_answers_proof_rows_conditions_and_empty_replay(case):
    ctx = deepcopy(case["context"])
    original = deepcopy(ctx)
    for key in ("answer", "solution"):
        section(ctx, key)["html"] = "<p>Не использовать: 999.</p>"
    untouched = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == untouched
    expected = sp.Rational(
        BeautifulSoup(section(original, "answer")["html"], "html.parser")
        .get_text()
        .replace(",", ".")
    )
    assert sp.Rational(result.answer.replace(",", ".")) == expected
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], selection(ctx)[0])
    assert plan(case, ctx).transformations == ()
    old, new = (
        BeautifulSoup(section(c, "condition")["html"], "html.parser")
        for c in (original, ctx)
    )
    for soup in (old, new):
        assert len(soup.find_all("img")) == 1
        soup.img.decompose()
    assert str(old) == str(new) and len(ctx["normalized_content"]["assets"]) == 1
    profile = get_group_profile(case["group"])
    handler = get_handler(profile.content_rule_key)
    assert (
        profile.source_group_id == GROUPS[case["group"]]["group_uuid"]
        and profile.existing_solution_policy == "rewrite"
    )
    assert handler.requires_frozen_manifest and handler.verify_content_readback


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_extra_instructions_fail_closed_in_public_preparation(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Удвойте ответ.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("group", list(GROUPS))
def test_changed_parent_methods_block_public_handler(group):
    case = next(c for c in CASES if c["task"] == group)
    with pytest.raises(ContentPlanError):
        plan(case, parent=parent_html(group) + "<p>Другой метод.</p>")


@pytest.mark.parametrize(
    "task,generated",
    [
        ("46095", False),
        ("46183", False),
        ("46265", True),
        ("46351", True),
        ("672809", False),
        ("46581", False),
        ("46799", False),
    ],
)
def test_offline_frozen_roundtrip_reuses_sources_or_replaces_preview_uuid(
    task, generated
):
    case = next(c for c in CASES if c["task"] == task)
    group = case["group"]
    gateway = OfflineGateway(case)
    source = PARENTS[group]["context"]["normalized_content"]["assets"][0]["asset_id"]
    rule = GROUPS[group]["rule"]
    kwargs = {"parent_solution_html": parent_html(group)}
    record = _prepared_record(
        gateway,
        {"problem_id": case["context"]["problem_id"], "source_problem_id": task},
        source,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared", record
    assert not gateway.uploads and not gateway.writes
    assert _apply_record(gateway, record, source, rule, **kwargs)["status"] == "applied"
    assert len(gateway.uploads) == int(generated) and len(gateway.writes) == 1
    assert (
        _apply_record(gateway, record, source, rule, **kwargs)["status"]
        == "already_complete"
    )


@pytest.mark.parametrize("task", ["46095", "46265"])
def test_missing_condition_change_fails_authoritative_offline_readback(task):
    case = next(c for c in CASES if c["task"] == task)
    group = case["group"]
    gateway = OfflineGateway(case, omit_condition_write=True)
    source = PARENTS[group]["context"]["normalized_content"]["assets"][0]["asset_id"]
    rule = GROUPS[group]["rule"]
    kwargs = {"parent_solution_html": parent_html(group)}
    record = _prepared_record(
        gateway,
        {"problem_id": case["context"]["problem_id"], "source_problem_id": task},
        source,
        rule,
        **kwargs,
    )
    assert record["status"] == "prepared"
    assert _apply_record(gateway, record, source, rule, **kwargs)["status"] == "failed"


def test_wrong_generated_checksum_is_rejected():
    case = next(c for c in CASES if c["task"] == "46265")
    group = case["group"]
    with pytest.raises(ContentPlanError):
        get_handler(GROUPS[group]["rule"]).plan(
            PlanInput(
                case["context"],
                parent_asset_id=PARENTS[group]["context"]["normalized_content"][
                    "assets"
                ][0]["asset_id"],
                parent_solution_html=parent_html(group),
                generated_solution_assets=(
                    {
                        "asset_key": KEY,
                        "sha256": "0" * 64,
                        "source_asset_id": "preview-bad",
                        "url": "/assets/preview-bad",
                    },
                ),
            )
        )


@pytest.mark.parametrize("kind", ["extra", "reference", "source", "url"])
def test_unknown_asset_or_mismatched_reference_cannot_be_silently_replaced(kind):
    case = CASES[0]
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    if kind == "extra":
        ctx["normalized_content"]["assets"].append(
            {"asset_key": "image_2", "asset_id": "other"}
        )
    elif kind == "reference":
        section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
            asset["asset_id"], "other"
        )
    elif kind == "source":
        asset["asset_id"] = "other"
        asset["url"] = "/assets/other"
    else:
        asset["url"] = "/assets/other"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "group,text",
    [
        ("27750", "Больший угол равнобедренного треугольника равен 70°"),
        ("27754", "Один угол равнобедренного треугольника на 30° больше другого"),
    ],
)
def test_ambiguous_comparisons_fail_closed_through_public_handler(group, text):
    case = PARENTS[group]
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    section(ctx, "condition")["html"] = (
        f"<p>{image}{text}. Найдите меньший угол. Ответ дайте в градусах.</p>"
    )
    with pytest.raises(ContentPlanError, match="two distinct"):
        plan(case, ctx)
