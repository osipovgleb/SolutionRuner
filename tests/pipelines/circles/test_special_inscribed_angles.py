"""Special chords share the inscribed-angle theorem without borrowed geometry."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from test_midpoint_area_lifecycle import OfflineGateway

from solution_runner.pipelines.circles.angle_model import read_question
from solution_runner.pipelines.core.content_runtime import (
    _apply_record,
    _prepared_record,
    _solution_assets,
)
from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_1_special_angle_sources.json"
    ).read_text()
)
CASES = DATA["cases"]
PARENT = CASES[0]["context"]
RULE = "circle-inscribed-special-chord"
ARGS = {
    "parent_asset_id": PARENT["normalized_content"]["assets"][0]["asset_id"],
    "parent_solution_html": section(PARENT, "solution")["html"],
    "parent_solution_assets": _solution_assets(PARENT),
}


def plan(context, **overrides):
    return get_handler(RULE).plan(PlanInput(context, **(ARGS | overrides)))


def verify(html, expected):
    names = {
        r"\angle BOC": 60,
        r"\angle BAC": expected,
        r"\alpha": expected,
        r"\varphi": 180,
        "BO": 1,
        "OC": 1,
        "BC": 1,
        "R": 1,
    }
    for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = tag["data-inline-latex"]
        for label, number in names.items():
            formula = formula.replace(label, f"({number})")
        formula = formula.replace(r"^{\circ}", "")
        values = [TrigonometricParser(p).parse().value for p in formula.split("=")]
        assert len(values) > 1
        assert all(sp.simplify(v - values[0]) == 0 for v in values)


@pytest.mark.parametrize(
    "case,answer", tuple(zip(CASES, (150, 90))), ids=("radius", "diameter")
)
def test_native_theorem_proof_and_exact_replay(case, answer):
    original = deepcopy(case["context"])
    result = plan(original)
    assert result.answer == str(answer)
    html = solution_html(result)
    verify(html, answer)
    assert original == case["context"]
    updated = deepcopy(original)
    replay(updated, result.transformations)
    assert not plan(updated).transformations
    assert section(updated, "condition") == section(original, "condition")
    assert len(BeautifulSoup(html, "html.parser").find_all("img")) == (answer == 150)
    assert not get_handler(RULE).diagram_specs(original)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_local_frozen_roundtrip_preserves_assets_and_resumes(case):
    gateway = OfflineGateway(case)
    record = _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        content_rule_key=RULE,
        **ARGS,
    )
    assert record["status"] == "prepared", record
    assert not gateway.writes and not gateway.uploads
    assert (
        _apply_record(gateway, record, content_rule_key=RULE, **ARGS)["status"]
        == "applied"
    )
    assert (
        _apply_record(gateway, record, content_rule_key=RULE, **ARGS)["status"]
        == "already_complete"
    )
    assert len(gateway.writes) == 1 and not gateway.uploads
    assert (
        gateway.context["normalized_content"]["assets"]
        == case["context"]["normalized_content"]["assets"]
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_frozen_condition_drift_blocks_before_any_mock_write(case):
    gateway = OfflineGateway(case)
    record = _prepared_record(
        gateway,
        {
            "problem_id": case["context"]["problem_id"],
            "source_problem_id": case["task"],
        },
        content_rule_key=RULE,
        **ARGS,
    )
    section(gateway.context, "condition")["html"] += "<p>Дополнительное условие</p>"
    assert _apply_record(gateway, record, content_rule_key=RULE, **ARGS)["status"] in {
        "failed",
        "blocked",
    }
    assert not gateway.writes and not gateway.uploads


@pytest.mark.parametrize(
    "field", ("parent_asset_id", "parent_solution_html", "parent_solution_assets")
)
def test_changed_parent_method_or_figure_is_refused(field):
    value = () if field == "parent_solution_assets" else "changed"
    with pytest.raises(ContentPlanError):
        plan(CASES[1]["context"], **{field: value})


@pytest.mark.parametrize(
    "suffix", (" Найдите также радиус.", " Ответ дайте в радианах.", " Угол острый.")
)
def test_extra_unread_condition_is_refused(suffix):
    ctx = deepcopy(CASES[1]["context"])
    section(ctx, "condition")["html"] += "<p>" + suffix + "</p>"
    with pytest.raises(ContentPlanError):
        plan(ctx)


@pytest.mark.parametrize(
    "description,expected",
    (("диаметр", 90), ("острый", 30), ("тупой", 150)),
)
def test_exact_arc_relation_instead_of_stored_answer(description, expected):
    ctx = deepcopy(CASES[1]["context"])
    question = (
        "Чему равен вписанный угол, опирающийся на диаметр окружности?"
        if description == "диаметр"
        else f"Чему равен {description} вписанный угол, опирающийся на хорду, равную радиусу окружности?"
    )
    section(ctx, "condition")["html"] = (
        "<p>" + question + " Ответ дайте в градусах.</p>"
    )
    section(ctx, "answer")["html"] = "<p>999</p>"
    assert read_question(section(ctx, "condition")["html"]).answer == expected
    result = plan(ctx)
    assert result.answer == str(expected)
    verify(solution_html(result), expected)
    replay(ctx, result.transformations)
    assert not plan(ctx).transformations


def test_wrong_chord_diagram_is_not_reused_for_diameter():
    ctx = deepcopy(PARENT)
    soup = BeautifulSoup(section(ctx, "condition")["html"], "html.parser")
    image = str(soup.find("img"))
    section(ctx, "condition")["html"] = (
        image + section(CASES[1]["context"], "condition")["html"]
    )
    with pytest.raises(ContentPlanError):
        plan(ctx)


def test_missing_radius_drawings_restore_exact_reviewed_assets():
    ctx = deepcopy(PARENT)
    for sec in ctx["normalized_content"]["sections"]:
        soup = BeautifulSoup(sec["html"], "html.parser")
        for img in soup.find_all("img"):
            img.decompose()
        sec["html"], sec["asset_keys"] = str(soup), []
    ctx["normalized_content"]["assets"] = []
    result = plan(ctx)
    updated = deepcopy(ctx)
    replay(updated, result.transformations)
    assert [
        (a["asset_key"], a["asset_id"], a["url"])
        for a in updated["normalized_content"]["assets"]
    ] == [
        (a["asset_key"], a["asset_id"], a["url"])
        for a in PARENT["normalized_content"]["assets"]
    ]
    assert section(updated, "condition")["asset_keys"] == ["image_1"]
    assert section(updated, "solution")["asset_keys"] == ["image_2"]
    assert not plan(updated).transformations


def test_explicit_group_binding_uses_shared_family():
    profile = get_group_profile("27859")
    assert profile.content_rule_key == RULE
    assert profile.theme_order_index == 5
