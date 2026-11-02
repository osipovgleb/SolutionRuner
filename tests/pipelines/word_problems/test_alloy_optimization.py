"""Native source tasks, independent feasible allocations and immutable chart reuse."""

import hashlib
import json
import math
from html import unescape
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.core.content_runtime import _with_required_assets
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.word_problems import alloy_optimization as model
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_17_alloy_optimization.json").read_text()
)
CASES = DATA["cases"]


def condition(context):
    return next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )


def plan(context):
    handler = get_handler(get_group_profile("513289").content_rule_key)
    prepared = _with_required_assets(context, handler.key)
    return handler.plan(PlanInput(prepared)), prepared


def test_full_catalog_group_is_eligible_and_uses_one_shared_rule():
    p = get_group_profile("513289")
    assert (p.category_key, p.group_order_index, p.theme_order_index) == ("17", 8, 0)
    assert p.source_group_id == DATA["binding"]["group"]["uuid"]
    assert p.snapshot_theme_id == DATA["binding"]["theme"]["uuid"]
    assert p.content_rule_key == "word-alloy-labor-optimization"
    assert p.existing_solution_policy == "rewrite"
    tasks = DATA["group_tasks"]
    assert len(tasks) == DATA["group_size"] == 3
    assert {t["uuid"] for t in tasks} == {c["context"]["problem_id"] for c in CASES}


@pytest.mark.parametrize(
    "case,expected",
    list(zip(CASES, ("60", "120", "60"))),
    ids=lambda x: x["task"] if isinstance(x, dict) else x,
)
def test_native_answers_follow_a_feasible_equal_metal_allocation(case, expected):
    context = deepcopy(case["context"])
    before = deepcopy(context)
    result, prepared = plan(context)
    _, a = model.calculate(context)
    assert result.answer == expected and context == before
    assert result.condition_html == condition(context)["html"]
    assert 2 * a.critical**2 == a.labor
    first_aluminium = a.first / 2
    assert 0 <= first_aluminium <= a.first
    assert first_aluminium / a.rate + (a.first - first_aluminium) / a.rate == a.labor
    assert 2 * (first_aluminium + a.critical) == sp.Rational(expected)
    assert all(
        t["transformation_target_id"].startswith(("section:solution", "section:answer"))
        for t in result.transformations
    )
    assert get_handler("word-alloy-labor-optimization").diagram_specs(prepared) == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_saved_answers_and_child_methods_are_unused_and_replay_is_empty(case):
    context = deepcopy(case["context"])
    for s in context["normalized_content"]["sections"]:
        if s["key"] in {"answer", "solution"}:
            s["html"] = "<p>UNUSED 999</p>"
    result, replay = plan(context)
    expected, _ = plan(case["context"])
    assert (
        result.answer == expected.answer
        and result.solution_html == expected.solution_html
    )
    for t in result.transformations:
        next(
            s
            for s in replay["normalized_content"]["sections"]
            if s["transformation_target_id"] == t["transformation_target_id"]
        ).update(t["value"])
    assert plan(replay)[0].transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_derivative_and_figure_stay_before_feasibility_and_final_mass(case):
    html = plan(case["context"])[0].solution_html
    soup = BeautifulSoup(html, "html.parser")
    formulas = [f["data-inline-latex"] for f in soup.select("[data-inline-latex]")]
    image = soup.find("img")
    assert image is not None and unescape(html).index("m'(x)=") < html.index(
        "<img"
    ) < html.index("максимум достижим")
    assert any(f.startswith("y=") for f in formulas)
    assert not any(r"\ge\frac{(x+y)" in f for f in formulas)
    _, a = model.calculate(case["context"])
    source, digest = model._CHARTS[a.critical]
    assert image["src"] == "/assets/" + source
    blob = (
        Path(model.__file__).with_name("assets").joinpath(source + ".svg").read_bytes()
    )
    assert hashlib.sha256(blob).hexdigest() == digest


@pytest.mark.parametrize("rate", ["0,2", "0,003", "0,001"])
def test_sampled_original_resource_constraints_bound_every_feasible_allocation(rate):
    context = deepcopy(CASES[0]["context"])
    condition(context)["html"] = condition(context)["html"].replace("0,2", rate)
    result, _ = plan(context)
    labor, critical = 200, 10
    first = 200 * float(rate.replace(",", "."))
    expected = first + 20
    sampled_max = 0.0
    for i in range(17):
        for j in range(17):
            aluminium, nickel = critical * i / 8, critical * j / 8
            if aluminium**2 + nickel**2 > labor:
                continue
            for k in range(17):
                first_aluminium = first * k / 16
                first_nickel = first - first_aluminium
                alloy = 2 * min(first_aluminium + aluminium, first_nickel + nickel)
                assert alloy <= expected + 1e-10
                sampled_max = max(sampled_max, alloy)
    assert math.isclose(sampled_max, expected)
    assert math.isclose(float(result.answer.replace(",", ".")), expected)


@pytest.mark.parametrize(
    "before,after",
    [
        ("0,2", "0"),
        ("x^{2}", "x^{3}"),
        ("y^{2}", "y^{3}"),
        ("на 1", "на 2"),
        ("готов трудиться", "не готов трудиться"),
    ],
)
def test_changed_resource_laws_or_alloy_ratio_fail_closed(before, after):
    context = deepcopy(CASES[0]["context"])
    original = condition(context)["html"].replace("\xad", "")
    assert before in original
    condition(context)["html"] = original.replace(before, after)
    assert condition(context)["html"] != original
    with pytest.raises(UnsupportedCondition):
        plan(context)


def test_unequal_first_region_rates_and_extra_questions_are_rejected():
    context = deepcopy(CASES[0]["context"])
    condition(context)["html"] = condition(context)["html"].replace("0,2", "0,3", 1)
    with pytest.raises(UnsupportedCondition, match="equal positive"):
        plan(context)
    context = deepcopy(CASES[0]["context"])
    condition(context)["html"] += "<p>Удвойте полученный ответ.</p>"
    with pytest.raises(UnsupportedCondition):
        plan(context)


def test_changed_budget_cannot_silently_reuse_old_chart_labels():
    context = deepcopy(CASES[0]["context"])
    condition(context)["html"] = condition(context)["html"].replace("по 20", "по 40", 1)
    with pytest.raises(UnsupportedCondition, match="audited sign chart"):
        plan(context)


def test_unknown_or_wrong_source_chart_is_rejected():
    for source in ("unknown", model._CHARTS[sp.Integer(20)][0]):
        context = deepcopy(CASES[0]["context"])
        asset = context["normalized_content"]["assets"][0]
        asset.update(asset_id=source, url="/assets/" + source)
        with pytest.raises(UnsupportedCondition, match="computed maximum"):
            plan(context)


def test_assetless_child_only_requests_existing_compatible_source():
    case = CASES[2]
    assert case["context"]["normalized_content"]["assets"] == []
    before = deepcopy(case["context"])
    requirements = get_handler("word-alloy-labor-optimization").asset_requirements(
        before
    )
    assert requirements == (
        {
            "source_asset_id": model._CHARTS[sp.Integer(10)][0],
            "section_id": "solution:1",
            "alt_text": model._ALT,
        },
    )
    assert case["context"] == before


def test_inline_decimal_rates_keep_exact_values():
    context = deepcopy(CASES[0]["context"])
    condition(context)["html"] = condition(context)["html"].replace(
        "0,2", '<span data-inline-latex="0{,}2"></span>'
    )
    assert model.calculate(context)[1].rate == sp.Rational(1, 5)
    assert plan(context)[0].answer == "60"
