"""Relative speed, train passing lengths, short time units and source repair."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_profile_percentages import plan
from test_profile_percentages import (
    test_existing_profile_alias_and_handler_are_reused_without_another_registration as verify_registration,
)
from test_profile_percentages import (
    test_source_answer_is_computed_without_mutation_and_replay_has_no_more_changes as verify_source,
)
from test_profile_percentages import (
    test_unknown_instructions_and_assets_fail_closed as verify_rejection,
)

from solution_runner.pipelines.word_problems import math_common
from solution_runner.pipelines.word_problems import relative_motion as model
from solution_runner.pipelines.word_problems.relative_motion_questions import duration

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_11_relative.json").read_text()
)
CASES = DATA["cases"]


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_six_groups_share_one_relative_displacement_rule(group):
    verify_registration(group)
    assert group["rule"] == "word-relative-displacement"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_saved_sources_compute_independently_and_replay_without_changes(case):
    verify_source(case)
    _, a = model.calculate(case["context"])
    q = a.question
    assert a.rate > 0 and a.result > 0
    if q.kind == "walk_gap":
        assert a.rate * (a.result / 60) == q.values["distance"] / 1000
    else:
        assert a.rate * q.time.total_seconds / 3600 == a.displacement
        if q.kind != "car_gap":
            assert a.result + q.values.get("obstacle", 0) == 1000 * a.displacement


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unread_instructions_and_foreign_assets_fail_closed(case, mode):
    verify_rejection(case, mode)


@pytest.mark.parametrize(
    "text,seconds",
    [
        ("36 секунд", 36),
        ("1 минуту", 60),
        ("6 минутам", 360),
        ("1 минуте 3 секундам", 63),
        ("1 минуту 48 секунд", 108),
        ("0,5 минуты", 30),
    ],
)
def test_minute_and_second_inflections_keep_exact_units(text, seconds):
    assert duration(text).total_seconds == seconds


@pytest.mark.parametrize(
    "text",
    [
        "0 секунд",
        "0 минут 0 секунд",
        "-1 минуту",
        "1 минуту -30 секунд",
        "1 час",
        "2 милисекунды",
        "минуту",
    ],
)
def test_unread_or_nonpositive_short_durations_fail_closed(text):
    with pytest.raises(ValueError):
        duration(text)


@pytest.mark.parametrize(
    "task,old,new,error",
    [
        ("99608", "80 км/ч", "0 км/ч", "positive speeds"),
        ("99608", "36 секунд", "0 секунд", "positive short duration"),
        ("99608", "36 секунд", "36 минут с остановкой", "complete relative-motion"),
        ("99608", "80 км/ч", "80 м/с", "complete relative-motion"),
        ("99609", "400 метрам", "1000 метрам", "positive train length"),
        ("99611", "90 км/ч", "30 км/ч", "positive relative speed"),
        ("99611", "90 км/ч", "20 км/ч", "positive relative speed"),
        ("99611", "600 метрам", "1000 метрам", "positive train length"),
        ("99612", "700 метрам", "1100 метрам", "positive train length"),
        ("99595", "300 метрам", "0 метрам", "positive speeds"),
        (
            "99595",
            "Через сколько минут",
            "Через сколько часов",
            "complete relative-motion",
        ),
        ("549340", "70 км/ч", "40 км/ч", "positive relative speed"),
        (
            "549340",
            "15 минут",
            "15 секунд до обгона и 15 минут",
            "complete relative-motion",
        ),
    ],
)
def test_changed_directions_lengths_units_and_questions_fail_closed(
    task, old, new, error
):
    context = deepcopy(case_for(task)["context"])
    text = math_common.read(context)[3]
    assert old in text
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + text.replace(old, new) + "</p>"
    with pytest.raises(ValueError, match=error):
        model.calculate(context)


@pytest.mark.parametrize("task", ["99611", "117739", "517197", "517235"])
def test_both_parent_methods_keep_order_and_convert_minutes_and_seconds(task):
    case = case_for(task)
    html = plan(case).solution_html
    sections = BeautifulSoup(html, "html.parser").select(
        'section[data-content-kind="solution"]'
    )
    assert len(sections) == 2
    assert sections[0]["data-solution-title"] == "Решение"
    assert sections[1]["data-solution-title"] == "Приведём другое решение"
    assert r"\mathrm{км}/\mathrm{мин}" in str(sections[0])
    assert r"\mathrm{м}/\mathrm{с}" in str(sections[1])
    expected = "=" + math_common.number(model.calculate(case["context"])[1].result)
    for section in sections:
        formulas = section.select("[data-inline-latex]")
        assert expected in formulas[-1]["data-inline-latex"]


def test_saved_dot_answer_is_repaired_by_the_distance_formula():
    case = case_for("116357")
    context = deepcopy(case["context"])
    saved = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    assert BeautifulSoup(saved, "html.parser").get_text() == "."
    result = plan(case, context)
    assert result.answer == "500"
    assert sp.Rational(60 * 1000, 3600) * 30 == 500
    assert any(
        t["transformation_target_id"].startswith("section:answer")
        for t in result.transformations
    )
    assert context == case["context"]


def test_meeting_train_rates_add_while_overtaking_rates_subtract():
    _, same = model.calculate(case_for("99611")["context"])
    _, opposite = model.calculate(case_for("99612")["context"])
    assert same.rate == 90 - 30 == 60
    assert opposite.rate == 65 + 35 == 100
