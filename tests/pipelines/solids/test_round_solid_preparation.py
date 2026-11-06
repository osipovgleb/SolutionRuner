"""Circular-solid native plans keep their methods, figures and write-free identity."""

from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from round_solid_source_cases import CASES, GROUPS, arguments, plan
from test_midpoint_area_lifecycle import OfflineGateway
from test_pyramid_midsections_lifecycle import without_figures
from test_round_solid_models import ANSWERS

from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids import (
    round_solid_sources,
    spatial_distance_sources,
)
from solution_runner.pipelines.solids.distance_figures import selection
from solution_runner.pipelines.solids.spatial_distance_model import read_question


def expected(case):
    return sp.latex(sp.simplify(ANSWERS[case["task"]]), inv_trig_style="full")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answer_figures_methods_and_idempotent_plan(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    assert result.answer == expected(case)
    assert ctx == case["context"]
    html = solution_html(result)
    soup = BeautifulSoup(html, "html.parser")
    assert len(soup.find_all("img")) == (2 if case["group"] == "520803" else 1)
    assert "\\" not in soup.get_text()
    if case["group"] in {"520803", "520938"}:
        assert ("Другое решение пункта а)" in soup.get_text()) == (
            case["group"] == "520803"
        )
    if case["group"] == "502023":
        assert "Другой способ нахождения радиуса" in soup.get_text()
    assert get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx) == ()
    assert all(
        not generated and source == old["asset_id"]
        for _, old, source, _, generated in selection(ctx)[-1]
    )
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations
    for key in ("condition", "criteria", "source"):
        assert section(ctx, key) == section(case["context"], key)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_plan_freezes_without_upload_or_write(case):
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
    assert record["expected_answer"] == expected(case)
    assert (
        not record["generated_diagrams"] and not gateway.uploads and not gateway.writes
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_missing_illustrations_restore_each_parents_methods(case):
    ctx = without_figures(case)
    result = plan(case, ctx)
    assert len(BeautifulSoup(solution_html(result), "html.parser").find_all("img")) == (
        2 if case["group"] == "520803" else 1
    )
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_parent_drift_extra_requirements_and_missing_conditions_refuse(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Найдите также объем.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_html="changed")
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_assets=())
    ctx["normalized_content"]["sections"] = [
        s for s in ctx["normalized_content"]["sections"] if s["key"] != "condition"
    ]
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_missing_answer_is_created_without_altering_the_condition_or_source():
    case = next(c for c in CASES if c["task"] == "511368")
    assert section(case["context"], "answer") is None
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    assert any(
        t["transformation_target_id"] == "section:answer"
        for t in result.transformations
    )
    replay(ctx, result.transformations)
    assert section(ctx, "answer") is not None
    assert not plan(case, ctx).transformations


def under_parent(task, group):
    original = next(c for c in CASES if c["task"] == task)
    return {**original, "group": group}


def test_parent_coordinate_method_is_retained_for_a_lateral_area_question():
    case = under_parent("520938", "520803")
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    html = solution_html(result)
    assert "Другое решение пункта а)" in BeautifulSoup(html, "html.parser").get_text()
    assert len(BeautifulSoup(html, "html.parser").find_all("img")) == 2
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations


def test_a_valid_existing_child_coordinate_method_is_not_dropped():
    case = under_parent("520803", "520938")
    result = plan(case)
    assert len(BeautifulSoup(solution_html(result), "html.parser").find_all("img")) == 2


def test_a_geometric_parent_does_not_gain_an_unrequested_coordinate_method():
    case = next(c for c in CASES if c["task"] == "520938")
    ctx = deepcopy(case["context"])
    from round_solid_source_cases import raw

    text = raw("520938").replace(
        "площадь боковой поверхности цилиндра", "угол между прямыми BB_1 и AC_1"
    )
    section(ctx, "condition")["html"] = "<p>" + text + "</p>"
    html = solution_html(plan(case, ctx))
    assert (
        "Другое решение пункта а)" not in BeautifulSoup(html, "html.parser").get_text()
    )
    assert len(BeautifulSoup(html, "html.parser").find_all("img")) == 1


def test_contradictory_parent_method_metadata_is_rejected():
    case = next(c for c in CASES if c["task"] == "520803")
    m = read_question(section(case["context"], "condition")["html"])
    with pytest.raises(ContentPlanError):
        round_solid_sources.reviewed_model(
            m,
            {},
            (
                "0c4a9dfb-2320-4701-9835-af73aadfb9d0",
                "4cad92bc-7ad5-4795-85f1-34dba7a08ac9",
            ),
            spatial_distance_sources.DATA["figures"],
        )


@pytest.mark.parametrize(
    "task,changes,answer",
    [
        (
            "502115",
            [("равна 8.", r"равна 3\pi."), ("равна 5.", r"равна 2\pi.")],
            5 * sp.pi,
        ),
        (
            "520803",
            [
                ("AB = 6", "AB = 3"),
                ("BB_1 = 15", "BB_1 = 5"),
                ("B_1C_1 = 8", "B_1C_1 = 4"),
            ],
            r"45^{\circ}",
        ),
        (
            "520879",
            [
                ("AB = 21", "AB = 3"),
                ("BB_1 = 12", "BB_1 = 4"),
                ("B_1C_1 = 16", "B_1C_1 = 5"),
            ],
            3 * sp.sqrt(82) / 10,
        ),
        (
            "520938",
            [
                ("AB = 20", "AB = 5"),
                ("BB_1 = 15", "BB_1 = 7"),
                ("B_1C_1 = 21", "B_1C_1 = 12"),
            ],
            91 * sp.pi,
        ),
        (
            "502023",
            [("равно 10,", "равно 15,"), ("равна 6,", "равна 9,")],
            144 * sp.pi * (11 - 4 * sp.sqrt(7)),
        ),
        (
            "514026",
            [("высотой 12", "высотой 5"), ("основания 6", "основания 3")],
            15 + 15 * sp.sqrt(3) / 2,
        ),
    ],
)
def test_changed_full_plans_compute_exact_answers_and_repeat_without_changes(
    task, changes, answer
):
    from round_solid_source_cases import changed

    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = "<p>" + changed(task, *changes) + "</p>"
    result = plan(case, ctx)
    assert result.answer == (
        answer
        if isinstance(answer, str)
        else sp.latex(sp.simplify(answer), inv_trig_style="full")
    )
    assert get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx) == ()
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize("task", ("502115", "520803", "502023", "514026"))
def test_foreign_reviewed_illustrations_are_not_silently_accepted(task):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    original = asset["asset_id"]
    foreign = "9f3ee955-ce64-4202-abd1-669a222624ec"
    asset["asset_id"], asset["url"] = foreign, "/assets/" + foreign
    section(ctx, "solution")["html"] = section(ctx, "solution")["html"].replace(
        original, foreign
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_a_coordinate_illustration_cannot_occupy_the_geometric_slot():
    case = next(c for c in CASES if c["task"] == "520803")
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    original = asset["asset_id"]
    wrong = "7b9ae11b-2b45-4730-ba03-b701d7d9cc58"
    asset["asset_id"], asset["url"] = wrong, "/assets/" + wrong
    section(ctx, "solution")["html"] = section(ctx, "solution")["html"].replace(
        original, wrong
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
