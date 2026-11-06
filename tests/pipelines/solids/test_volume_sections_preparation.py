"""Native plans preserve their illustrations, freeze without writes and resume unchanged."""

from copy import deepcopy

import pytest
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from test_midpoint_area_lifecycle import OfflineGateway
from test_pyramid_midsections_lifecycle import without_figures
from volume_sections_source_cases import CASES, GROUPS, arguments, plan

from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.distance_figures import selection

ANSWERS = {
    "484567": r"60^{\circ}",
    "511467": r"\frac{1}{6}",
    "507675": r"\frac{1}{4}",
    "501436": "3",
    "501456": "6",
    "511360": "24",
    "501549": r"\frac{375 \sqrt{3}}{8}",
    "501555": "24",
    "505241": "24",
    "511363": r"\frac{81}{8}",
    "517446": "13:23",
    "517439": "21:11",
    "517453": "9:23",
}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_preparation_preserves_assets_and_repeats_without_changes(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    assert result.answer == ANSWERS[case["task"]]
    assert ctx == case["context"]
    html = solution_html(result)
    assert len(BeautifulSoup(html, "html.parser").find_all("img")) == 1
    assert "\\" not in BeautifulSoup(html, "html.parser").get_text()
    assert get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx) == ()
    _, _, _, _, figures = selection(ctx)
    assert all(
        not generated and source == old["asset_id"]
        for _, old, source, _, generated in figures
    )
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations
    for key in ("condition", "criteria", "source"):
        assert section(ctx, key) == section(case["context"], key)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_context_freezes_without_uploads_or_writes(case):
    gateway = OfflineGateway(case)
    record = _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        content_rule_key=GROUPS[case["group"]]["rule"],
        **arguments(case["group"]),
    )
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == ANSWERS[case["task"]]
    assert not record["generated_diagrams"]
    assert not gateway.uploads and not gateway.writes


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_missing_figures_restore_the_correct_variant_and_remain_idempotent(case):
    ctx = without_figures(case)
    result = plan(case, ctx)
    assert len(BeautifulSoup(solution_html(result), "html.parser").find_all("img")) == 1
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_extra_requirements_and_parent_drift_refuse(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Найдите также площадь.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_html="changed")
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_assets=())


@pytest.mark.parametrize(
    "task,changes",
    [
        ("484567", [("равны 1,", "равны 3,"), ("равны 2,", "равны 10,")]),
        ("501436", [("8\\sqrt{3}", "7"), ("основания равно 1.", "основания равно 5.")]),
        ("501549", [("10\\sqrt{3}", "5")]),
        ("517446", [("1: 2.", "5: 7.")]),
    ],
)
def test_resized_full_plans_preserve_their_reviewed_unnumbered_scenes(task, changes):
    from volume_sections_source_cases import replace

    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = "<p>" + replace(task, *changes) + "</p>"
    result = plan(case, ctx)
    assert get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx) == ()
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize(
    "task,source",
    [
        ("501456", "0af8f9a4-e6be-4ed3-adc4-f1a9dbd92a24"),
        ("511467", "9f3ee955-ce64-4202-abd1-669a222624ec"),
        ("505241", "66698c94-9d6c-4e6e-b08b-325f23836809"),
    ],
)
def test_a_known_figure_from_another_variant_is_replaced(task, source):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    original = asset["asset_id"]
    asset["asset_id"], asset["url"] = source, "/assets/" + source
    section(ctx, "solution")["html"] = section(ctx, "solution")["html"].replace(
        original, source
    )
    result = plan(case, ctx)
    selected = selection(ctx)[-1]
    assert len(selected) == 1 and selected[0][2] == original
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations


def test_an_unreviewed_centroid_figure_is_not_used_for_a_midline_cut():
    from volume_sections_source_cases import replace

    case = next(c for c in CASES if c["task"] == "501549")
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = (
        "<p>"
        + replace(
            "501549",
            ("BT: TM = 3: 1", "BT: TM = 1: 1"),
            ("отношении 1: 2", "отношении 1: 1"),
        )
        + "</p>"
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
