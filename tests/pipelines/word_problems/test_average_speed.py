"""Exact total-distance/total-time averages for four road-motion forms."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
import sympy as sp
from test_profile_percentages import (
    test_existing_profile_alias_and_handler_are_reused_without_another_registration as verify_registration,
)
from test_profile_percentages import (
    test_source_answer_is_computed_without_mutation_and_replay_has_no_more_changes as verify_source,
)
from test_profile_percentages import (
    test_unknown_instructions_and_assets_fail_closed as verify_rejection,
)

from solution_runner.pipelines.word_problems import average_speed as model
from solution_runner.pipelines.word_problems import math_common

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_11_averages.json").read_text()
)
CASES = DATA["cases"]


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_all_four_forms_share_one_average_speed_rule(group):
    verify_registration(group)
    assert group["rule"] == "word-average-speed"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_saved_sources_replay_without_saved_answer_dependency(case):
    verify_source(case)
    _, a = model.calculate(case["context"])
    assert min(a.question.speeds) <= a.result <= max(a.question.speeds)
    assert sum(a.distances) == a.result * sum(a.times)
    assert all(t > 0 for t in a.times)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_extra_instructions_and_foreign_assets_cannot_be_ignored(case, mode):
    verify_rejection(case, mode)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_units_and_segment_order_do_not_change_the_total_average(case):
    _, a = model.calculate(case["context"])
    q = a.question
    reordered = replace(q, speeds=q.speeds[::-1], weights=q.weights[::-1])
    assert model.analyze(reordered).result == a.result
    scaled_weights = replace(q, weights=tuple(7 * w for w in q.weights))
    assert model.analyze(scaled_weights).result == a.result
    scaled_speeds = replace(q, speeds=tuple(3 * v for v in q.speeds))
    assert model.analyze(scaled_speeds).result == 3 * a.result


def test_equal_times_and_equal_distances_require_different_means():
    speeds = (sp.Integer(30), sp.Integer(60), sp.Integer(90))
    time = model.analyze(model.Question("time", speeds, (sp.Integer(1),) * 3))
    distance = model.analyze(model.Question("distance", speeds, (sp.Integer(1),) * 3))
    assert time.result == 60
    assert distance.result == sp.Rational(540, 11)
    assert distance.times == (
        sp.Rational(1, 30),
        sp.Rational(1, 60),
        sp.Rational(1, 90),
    )


@pytest.mark.parametrize(
    "task,old,new,error",
    [
        ("99603", "74 км/ч", "0 км/ч", "positive leg speeds"),
        ("99603", "74 км/ч", "-74 км/ч", "positive leg speeds"),
        ("99605", "треть трассы", "четверть трассы", "complete average-speed"),
        ("99605", "110 км/ч", "110 м/с", "complete average-speed"),
        ("99606", "два часа", "0 часов", "positive duration"),
        ("99606", "два часа", "два дня", "complete average-speed"),
        ("99607", "190 км", "0 км", "positive leg speeds"),
        ("99607", "Найдите среднюю", "Найдите максимальную", "complete average-speed"),
    ],
)
def test_nonphysical_legs_unknown_units_and_changed_questions_fail_closed(
    task, old, new, error
):
    case = next(c for c in CASES if c["task"] == task)
    context = deepcopy(case["context"])
    text = math_common.read(context)[3]
    assert old in text
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + text.replace(old, new) + "</p>"
    with pytest.raises(ValueError, match=error):
        model.calculate(context)


def test_explicit_single_hour_in_last_segment_is_not_lost():
    case = next(c for c in CASES if c["task"] == "115355")
    _, a = model.calculate(case["context"])
    assert a.times == (3, 1, 1)
    assert a.distances == (210, 65, 45) and a.result == 64


def test_unrequested_rounding_is_not_used_for_a_changed_speed():
    case = next(c for c in CASES if c["task"] == "99605")
    context = deepcopy(case["context"])
    text = math_common.read(context)[3]
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + text.replace("110 км/ч", "109 км/ч") + "</p>"
    with pytest.raises(ValueError, match="non-terminating decimal"):
        model.build_context_repair_plan(context)
