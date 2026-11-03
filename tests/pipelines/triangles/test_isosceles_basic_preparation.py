"""Public preparation preserves methods, figures and authoritative local replay."""

import xml.etree.ElementTree as ET
from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from isosceles_basic_cases import CASES, GROUPS, PARENTS, parent_html, plan, section
from test_isosceles_basic_model import PARAMETERS, coordinates, verify_rows
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
from solution_runner.pipelines.triangles.isosceles.basic_figures import (
    BARE,
    GENERATED_KEY,
    HEIGHT,
    source_bytes,
    uncropped_svg,
)


def solution(result):
    return next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_public_plans_use_independent_answers_and_each_parent_method(case):
    result = plan(case)
    values = coordinates(*PARAMETERS[case["task"]])
    verify_rows(solution(result), values)
    assert float(result.answer.replace(",", ".")) == pytest.approx(
        float(values["AB" if case["group"] in {"27284", "27286", "27288"} else "AC"])
    )
    p = get_group_profile(case["group"])
    assert (
        p.existing_solution_policy == "rewrite"
        and p.source_group_id == GROUPS[case["group"]]["group_uuid"]
    )
    assert GROUPS[case["group"]]["group_size"] >= 3
    assert get_handler(p.content_rule_key).requires_frozen_manifest


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_stale_answers_are_unused_context_immutable_and_repeat_empty(case):
    ctx = deepcopy(case["context"])
    for key in ["solution", "answer"]:
        section(ctx, key)["html"] = "<p>Не использовать старое решение: 999.</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    assert ctx == before and result.answer == plan(case).answer
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    old = BeautifulSoup(section(before, "condition")["html"], "html.parser")
    new = BeautifulSoup(section(ctx, "condition")["html"], "html.parser")
    for soup in (old, new):
        for image in soup.find_all("img"):
            image.decompose()
    assert str(old) == str(new)


def test_uncropped_canvas_changes_no_vector_geometry_or_glyphs():
    old = ET.fromstring(source_bytes(BARE))
    new = ET.fromstring(uncropped_svg())
    assert [ET.tostring(c) for c in old] == [ET.tostring(c) for c in new]
    x, y, w, h = map(float, new.get("viewBox").split())
    for rect in new.iter("{http://www.w3.org/2000/svg}rect"):
        rx, ry = float(rect.get("x", 0)), float(rect.get("y", 0))
        assert x < rx < rx + float(rect.get("width")) < x + w
        assert y < ry < ry + float(rect.get("height")) < y + h


def test_missing_condition_figure_is_relocated_without_a_duplicate():
    case = next(c for c in CASES if c["task"] == "31797")
    ctx = deepcopy(case["context"])
    replay(ctx, plan(case, ctx).transformations)
    assert len(ctx["normalized_content"]["assets"]) == 1
    assert (
        len(
            BeautifulSoup(section(ctx, "condition")["html"], "html.parser").find_all(
                "img"
            )
        )
        == 1
    )
    assert not BeautifulSoup(section(ctx, "solution")["html"], "html.parser").find(
        "img"
    )


@pytest.mark.parametrize("task", ["27289", "31891", "31893", "31895"])
def test_separate_construction_stays_in_solution_only_when_not_already_in_condition(
    task,
):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    replay(ctx, plan(case, ctx).transformations)
    assets = ctx["normalized_content"]["assets"]
    if task == "31891":
        assert len(assets) == 1 and assets[0]["asset_id"] == HEIGHT
        assert not BeautifulSoup(section(ctx, "solution")["html"], "html.parser").find(
            "img"
        )
    else:
        assert {a["asset_key"] for a in assets} == {GENERATED_KEY, "image_2"}
        assert section(ctx, "solution")["asset_keys"] == ["image_2"]
        assert (
            BeautifulSoup(section(ctx, "solution")["html"], "html.parser").img[
                "data-asset-id"
            ]
            == HEIGHT
        )


@pytest.mark.parametrize("task", ["31797", "31891", "31893"])
def test_offline_frozen_lifecycle_preserves_figure_roles_and_parent_methods(task):
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
    assert record["status"] == "prepared" and not gateway.uploads and not gateway.writes
    result = _apply_record(gateway, record, source, rule, **kwargs)
    assert result["status"] == "applied", result
    assert (
        _apply_record(gateway, record, source, rule, **kwargs)["status"]
        == "already_complete"
    )
    assert (
        len(gateway.uploads) == (1 if task == "31893" else 0)
        and len(gateway.writes) == 1
    )


@pytest.mark.parametrize("group", list(GROUPS))
def test_unreviewed_parent_html_fails_closed(group):
    case = next(c for c in CASES if c["task"] == group)
    with pytest.raises(ContentPlanError):
        plan(case, parent=parent_html(group) + "<p>Еще один способ.</p>")


def test_unknown_primary_figure_fails_closed():
    case = next(c for c in CASES if c["task"] == "27284")
    ctx = deepcopy(case["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_nonterminating_platform_answer_is_not_silently_rounded():
    case = next(c for c in CASES if c["task"] == "27286")
    ctx = deepcopy(case["context"])
    image = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").img
    section(ctx, "condition")["html"] = (
        "<p>"
        + str(image)
        + r"В треугольнике ABC AC=BC=1, \cos A=\frac{1}{3}. Найдите AB.</p>"
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_prepared_uncropped_svg_checksum_must_match_the_original_vectors():
    from solution_runner.pipelines.core.handlers import PlanInput

    case = next(c for c in CASES if c["task"] == "27289")
    context = case["context"]
    generated = (
        {
            "asset_key": GENERATED_KEY,
            "source_asset_id": "preview-invalid",
            "url": "/assets/preview-invalid",
            "sha256": "0" * 64,
        },
    )
    with pytest.raises(ContentPlanError):
        get_handler(GROUPS[case["group"]]["rule"]).plan(
            PlanInput(
                context,
                parent_asset_id=BARE,
                parent_solution_html=parent_html(case["group"]),
                parent_solution_assets=_solution_assets(context),
                generated_solution_assets=generated,
            )
        )


def test_missing_parent_solution_figure_metadata_is_not_reconstructed_from_old_answer():
    from solution_runner.pipelines.core.handlers import PlanInput

    case = next(c for c in CASES if c["task"] == "27289")
    with pytest.raises(ContentPlanError):
        get_handler(GROUPS[case["group"]]["rule"]).plan(
            PlanInput(
                case["context"],
                parent_asset_id=BARE,
                parent_solution_html=parent_html(case["group"]),
            )
        )
