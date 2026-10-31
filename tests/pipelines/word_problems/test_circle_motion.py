"""Lap displacement, racing time balances and strictly future clock meetings."""

import hashlib
import json
from copy import deepcopy
from fractions import Fraction
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

from solution_runner.pipelines.word_problems import clock_meetings as clock
from solution_runner.pipelines.word_problems import (
    math_common,
    motion_models,
    relative_motion,
)

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_11_circle.json").read_text()
)
CASES = DATA["cases"]


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


def changed(case, old, new):
    context = deepcopy(case["context"])
    prepared = deepcopy(context)
    prepared["normalized_content"]["assets"] = []
    for s in prepared["normalized_content"]["sections"]:
        s["asset_keys"] = []
    text = math_common.read(prepared)[3]
    assert old in text
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + text.replace(old, new) + "</p>"
    return context


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_circle_groups_extend_the_existing_motion_families(group):
    verify_registration(group)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_sources_replay_without_saved_answer_dependency(case):
    verify_source(case)
    if case["group"] == "99600":
        _, a, _, _ = clock.calculate(case["context"])
        assert a.first > 0 and a.result == a.first + (a.question.count - 1) * a.interval
        difference = sp.Rational(60 * a.question.hour - 11 * a.question.minute, 2)
        assert (sp.Rational(11, 2) * a.result - difference) % 360 == 0
    elif case["group"] == "323856":
        _, a = motion_models.calculate(case["context"])
        v, q = a.question.values, a.question
        assert (a.result + v["gap"]) * q.durations[
            "lap_time"
        ].total - a.result * q.durations["lap_time"].total == v["circumference"]
        assert (
            v["distance"] / a.result - v["distance"] / (a.result + v["gap"])
            == q.durations["delay"].total
        )
        assert q.durations["lap_time"].total < v["distance"] / (a.result + v["gap"])
    else:
        _, a = relative_motion.calculate(case["context"])
        v = a.question.values
        if case["group"] == "99596":
            assert a.rate * a.result / 60 == v["distance"] / 2
        elif case["group"] == "99598":
            assert (v["first"] - a.result) * a.question.time.total_seconds / 3600 == v[
                "distance"
            ]
        else:
            bicycle = a.result - a.rate
            assert (
                bicycle * (v["lag_minutes"] + v["catch_minutes"])
                == a.result * v["catch_minutes"]
            )
            assert a.rate * v["lap_minutes"] / 60 == v["distance"]
            assert bicycle * v["lag_minutes"] / 60 < v["distance"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unknown_instructions_and_foreign_figures_fail_closed(case, mode):
    verify_rejection(case, mode)


@pytest.mark.parametrize("task", ["99600", "114655", "114661", "114773"])
def test_all_five_clock_methods_general_theorem_and_example_are_retained(task):
    result = plan(case_for(task))
    sections = BeautifulSoup(result.solution_html, "html.parser").select(
        'section[data-content-kind="solution"]'
    )
    assert len(sections) == 5
    titles = [s["data-solution-title"] for s in sections]
    assert "арифметическое" in titles[1] and "короткое" in titles[2]
    assert "геометрической прогрессии" in titles[3] and "общем виде" in titles[4]
    assert "Эмиль Бахшинян" in titles[3]
    assert "8 часов 20 минут" in sections[3].get_text()
    assert r"60h-11m+720j+720(n-1)" in str(sections[4])
    assert result.answer in str(sections[0])
    assert result.answer in str(sections[1])
    assert result.answer in str(sections[2])
    assert result.answer in str(sections[3])
    assert result.answer in str(sections[4])


def test_clock_meetings_agree_with_independent_absolute_angle_event_enumeration():
    for hour in range(12):
        for minute in [0, 5, 35, 59]:
            current = 60 * hour + minute
            events = [
                Fraction(720 * k, 11) - current
                for k in range(1, 40)
                if Fraction(720 * k, 11) > current
            ]
            for count in [1, 5, 11]:
                a = clock.analyze(clock.Question(hour, minute, count))
                assert Fraction(a.result) == events[count - 1]
                assert Fraction(a.first) == events[0]


def test_initial_coincidence_is_excluded_and_twelve_hour_aliases_agree():
    a = clock.analyze(clock.Question(0, 0, 1))
    assert a.first == sp.Rational(720, 11) and a.result > 0
    assert clock.parse(
        "Часы со стрелками показывают 12 часов ровно. Через сколько минут минутная стрелка в 11-й раз поравняется с часовой?"
    ) == clock.Question(0, 0, 11)
    context = changed(case_for("99600"), "8 часов ровно", "20 часов ровно")
    assert plan(case_for("99600"), context).answer == "240"


def test_exact_clock_image_is_preserved_after_first_method_without_asset_writes():
    case = case_for("114773")
    assert (
        hashlib.sha256(
            (Path(__file__).parent / "fixtures/clock_1_35.png").read_bytes()
        ).hexdigest()
        == clock.ASSET_SHA256
    )
    result = plan(case)
    soup = BeautifulSoup(result.solution_html, "html.parser")
    image = soup.find("img")
    assert image["data-asset-id"] == clock.ASSET_ID
    assert image["src"] == "/assets/" + clock.ASSET_ID
    assert image.find_parent("section")["data-solution-title"] == "Решение"
    assert len(soup.find_all("img")) == 1
    assert all(
        t["transformation_target_id"].startswith(("section:solution", "section:answer"))
        for t in result.transformations
    )
    assert next(
        t
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )["value"]["asset_keys"] == [image["data-asset-key"]]


@pytest.mark.parametrize(
    "mode", ["time", "identity", "url", "reference", "dangling", "extra", "link"]
)
def test_clock_figure_identity_references_and_compatibility_are_strict(mode):
    case = case_for("114773")
    context = deepcopy(case["context"])
    content = context["normalized_content"]
    solution = next(s for s in content["sections"] if s["key"] == "solution")
    if mode == "time":
        context = changed(case, "1 час 35 минут", "2 часа 35 минут")
    elif mode == "identity":
        content["assets"][0]["asset_id"] = "unknown-clock"
    elif mode == "url":
        content["assets"][0]["url"] = "/assets/foreign"
    elif mode == "reference":
        solution["html"] = solution["html"].replace(
            'data-asset-key="image_1"', 'data-asset-key="image_2"'
        )
    elif mode == "dangling":
        content["assets"] = []
    elif mode == "link":
        solution["html"] += '<a href="/assets/foreign">Другой рисунок</a>'
    else:
        content["assets"].append(dict(content["assets"][0]))
    with pytest.raises(ValueError):
        plan(case, context)


@pytest.mark.parametrize(
    "task,old,new,error",
    [
        ("99596", "14 км", "0 км", "positive speeds"),
        (
            "99596",
            "диаметрально противоположных",
            "различных",
            "complete relative-motion",
        ),
        ("99598", "80 км/ч", "21 км/ч", "positive speed"),
        ("99599", "Через 10 минут", "Через 30 минут", "must not have completed"),
        ("99599", "в первый раз", "в третий раз", "complete relative-motion"),
        ("323856", "60 кругов", "1 кругов", "exact rational physical root"),
        ("323856", "60 кругов", "60,5 кругов", "integral number"),
        ("323856", "15 минут", "0 минут", "positive duration"),
        ("99600", "8 часов ровно", "24 часа ровно", "valid clock time"),
        ("99600", "8 часов ровно", "8 часов 60 минут", "valid clock time"),
        ("99600", "четвертый", "0-й", "positive future meeting"),
        ("99600", "минутная стрелка", "секундная стрелка", "complete clock-hand"),
    ],
)
def test_nonphysical_laps_wrong_meeting_numbers_and_unknown_instructions_fail_closed(
    task, old, new, error
):
    case = case_for(task)
    with pytest.raises(ValueError, match=error):
        plan(case, changed(case, old, new))


def test_clock_answer_is_not_rounded_when_the_requested_meeting_is_fractional():
    case = case_for("99600")
    with pytest.raises(ValueError, match="non-terminating decimal"):
        plan(case, changed(case, "четвертый", "первый"))


def test_one_lap_catch_cannot_be_reported_after_the_faster_racer_finished():
    case = case_for("323856")
    context = changed(case, "60 кругов", "1 кругов")
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace("10 минут", "20 минут")
    with pytest.raises(ValueError, match="precede the finish"):
        plan(case, context)


def test_unlisted_clock_attachment_is_not_silently_discarded():
    case = case_for("99600")
    context = deepcopy(case["context"])
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "solution"
    )["html"] += '<a href="/assets/foreign">Чужой рисунок</a>'
    with pytest.raises(ValueError, match="audited metadata"):
        plan(case, context)
