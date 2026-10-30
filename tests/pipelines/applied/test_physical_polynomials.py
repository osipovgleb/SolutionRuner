"""Read source questions and retain only physically meaningful polynomial roots."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.applied import common
from solution_runner.pipelines.applied import physical_polynomials as model
from solution_runner.pipelines.applied.physical_questions import Question
from solution_runner.pipelines.calculus.common import T
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.core.numbers import parse_rational

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_10_physical.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


def plan(case, context):
    handler = get_handler(get_group_profile(case["group"]).content_rule_key)
    return handler.plan(PlanInput(context))


def solution(result):
    return next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_groups_register_one_shared_physical_family(group):
    profile = get_group_profile(group["key"])
    assert profile.source_group_id == group["uuid"]
    assert profile.snapshot_theme_id == group["theme_uuid"]
    assert profile.content_rule_key == group["rule"]
    assert profile.group_order_index == group["order"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_answers_are_computed_without_mutation_and_plans_are_idempotent(case):
    context = deepcopy(case["context"])
    original = deepcopy(context)
    expected = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    result = plan(case, context)
    assert parse_rational(result.answer) == parse_rational(
        BeautifulSoup(expected, "html.parser").get_text()
    )
    assert original == context
    assert all(
        t["transformation_target_id"].startswith(("section:answer", "section:solution"))
        for t in result.transformations
    )
    next(s for s in context["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999999</p>"
    assert plan(case, context).answer == result.answer
    context = deepcopy(original)
    sections = context["normalized_content"]["sections"]
    for t in result.transformations:
        section = next(
            (
                s
                for s in sections
                if s["transformation_target_id"] == t["transformation_target_id"]
            ),
            None,
        )
        if section is None:
            key = t["transformation_target_id"].split(":")[1]
            section = {
                "key": key,
                "section_id": key + ":1",
                "transformation_target_id": t["transformation_target_id"],
            }
            sections.append(section)
        section.update(t["value"])
    assert plan(case, context).transformations == ()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_additional_instructions_and_foreign_assets_are_refused(case, leading):
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    extra = "<p>Выберите больший корень независимо от смысла задачи.</p>"
    condition["html"] = (
        extra + condition["html"] if leading else condition["html"] + extra
    )
    with pytest.raises(ValueError):
        plan(case, context)
    context = deepcopy(case["context"])
    context["normalized_content"]["assets"] = [
        {"asset_id": "foreign", "asset_key": "image_1"}
    ]
    with pytest.raises(ValueError):
        plan(case, context)


def test_tank_draining_rejects_the_larger_root_after_emptying():
    _, a = model.calculate(sample("27959")["context"])
    assert a.roots == (50, 150)
    assert a.physical_end == 100 and a.selected == (50,)
    assert a.question.target == 5


def test_braking_rejects_returning_motion_after_stopping():
    case = sample("27965")
    _, a = model.calculate(case["context"])
    assert a.roots == (2, 6) and a.physical_end == 4
    assert a.selected == (2,)
    html = solution(plan(case, case["context"]))
    assert "движение назад" in html and "v(t)=" in html
    at_stop = model.analyze(replace(a.question, target=sp.Integer(40)))
    assert at_stop.result == 4 and at_stop.selected == (4,)
    assert "Единственный корень" in model.physical_proof.proof(at_stop)
    with pytest.raises(ValueError):
        model.analyze(replace(a.question, target=sp.Integer(41)))


def test_heater_uses_the_first_unsafe_crossing_instead_of_later_cooling():
    _, a = model.calculate(sample("27962")["context"])
    assert a.roots == (2, 18) and a.result == 2
    with pytest.raises(ValueError, match="no later unsafe"):
        model.analyze(replace(a.question, target=sp.Integer(2400)))
    with pytest.raises(ValueError, match="start safe"):
        model.analyze(replace(a.question, target=sp.Integer(1300)))


def test_acceleration_keeps_time_nonnegative_and_converts_hours_to_minutes():
    _, a = model.calculate(sample("27964")["context"])
    assert a.roots == (-10, sp.Rational(1, 2))
    assert a.selected == (sp.Rational(1, 2),) and a.result == 30
    assert a.question.scale == 60


def test_projectile_chooses_the_farthest_point_still_above_the_wall_clearance():
    _, a = model.calculate(sample("27961")["context"])
    assert a.question.target == 9 and a.selected == (10, 90) and a.result == 90
    with pytest.raises(ValueError):
        model.analyze(replace(a.question, target=sp.Integer(26)))


def test_duration_clips_to_start_and_handles_a_tangent_level_or_unreachable_level():
    q = Question("duration", -T * T + 2 * T + 3, sp.Integer(0))
    a = model.analyze(q)
    assert a.roots == (-1, 3) and a.interval == (0, 3) and a.result == 3
    tangent = model.analyze(replace(q, target=sp.Integer(4)))
    assert tangent.roots == (1,) and tangent.result == 0
    missing = model.analyze(replace(q, target=sp.Integer(5)))
    assert missing.roots == () and missing.result == 0


def test_rising_water_shortens_fall_time_and_rejects_a_negative_measurement():
    _, a = model.calculate(sample("27955")["context"])
    assert a.measurements == (
        sp.Rational(3, 5),
        sp.Rational(2, 5),
        sp.Rational(9, 5),
        sp.Rational(4, 5),
    )
    assert a.result == 1
    with pytest.raises(ValueError, match="measurements"):
        model.analyze(
            replace(
                a.question,
                values={"before": sp.Rational(1, 10), "change": sp.Integer(1)},
            )
        )


def test_subscript_normalization_does_not_consume_the_outer_root_brace():
    text = common.read(sample("27959")["context"])[3]
    assert r"\sqrt{2gH_0}kt" in text
    assert r"\sqrt{2gH_0kt" not in text


def test_formula_is_parsed_and_cannot_silently_contradict_the_given_acceleration():
    _, a = model.calculate(sample("27965")["context"])
    with pytest.raises(ValueError, match="contradicts"):
        model.analyze(replace(a.question, expression=-5 * T * T + 20 * T))
    with pytest.raises(ValueError, match="quadratic"):
        model.analyze(replace(a.question, expression=T**3))


def test_unit_changes_and_ambiguous_mathematical_markup_are_refused():
    case = sample("27964")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = (
        condition["html"].replace("\u00ad", "").replace("часах", "минутах")
    )
    with pytest.raises(ValueError):
        plan(case, context)
    case = sample("676852")
    context = deepcopy(case["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] += '<p><sub class="value">0</sub></p>'
    with pytest.raises(ValueError, match="subscripts"):
        plan(case, context)
