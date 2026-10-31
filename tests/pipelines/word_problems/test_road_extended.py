"""All remaining straight-road groups share the original exact balance solver."""

import json
from copy import deepcopy
from dataclasses import replace
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

from solution_runner.pipelines.calculus.common import answer
from solution_runner.pipelines.word_problems import math_common
from solution_runner.pipelines.word_problems import motion_models as model

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_11_road_extended.json").read_text()
)
CASES = DATA["cases"]


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_existing_time_balance_handler_covers_all_eight_groups(group):
    verify_registration(group)
    assert group["rule"] == "word-motion-time-balance"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_sources_compute_independently_and_replay_without_changes(case):
    verify_source(case)
    _, a = model.calculate(case["context"])
    assert a.result > 0
    assert a.balance.domain.contains(a.root) is sp.true
    assert sp.simplify((a.balance.left - a.balance.right).subs(model.X, a.root)) == 0
    assert all(d.subs(model.X, a.root) != 0 for d in a.balance.denominators)
    assert a.balance.output.subs(model.X, a.root) == a.result


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_extra_instructions_and_foreign_assets_cannot_be_ignored(case, mode):
    verify_rejection(case, mode)


@pytest.mark.parametrize(
    "case",
    [c for c in CASES if c["group"] in {"99594", "99597"}],
    ids=lambda c: c["task"],
)
def test_both_catching_methods_agree_and_keep_order(case):
    _, a = model.calculate(case["context"])
    other = model.alternate(a.question)
    assert other.result == a.result
    assert other.balance.domain.contains(other.root) is sp.true
    html = plan(case).solution_html
    sections = BeautifulSoup(html, "html.parser").select(
        'section[data-content-kind="solution"]'
    )
    assert len(sections) == 2 and sections[0]["data-solution-title"] == "Решение"
    assert sections[1]["data-solution-title"].startswith("Привед")
    expected = "=" + math_common.number(a.result)
    assert all(
        expected in s.select("[data-inline-latex]")[-1]["data-inline-latex"]
        for s in sections
    )
    if a.question.kind == "catch_return":
        distance, fast = (a.question.values[k] for k in ("distance", "known"))
        lag = a.question.durations["delay"].total
        assert 0 < other.root < fast
        assert 0 < a.result < distance
        assert other.root * (a.root + lag) == a.result
        assert other.root * (2 * a.root + lag) == distance
        assert fast * a.root == a.result
    else:
        first, second = (a.question.values[k] for k in ("first", "second"))
        gap = a.question.durations["delay"].total
        assert a.result > max(first, second)
        assert a.result * a.root == second * (a.root + 1)
        assert a.result * (a.root + gap) == first * (a.root + gap + 2)


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["group"] == "323849"], ids=lambda c: c["task"]
)
def test_all_five_walker_methods_and_total_distance_comment_are_preserved(case):
    _, a = model.calculate(case["context"])
    v = a.question.values
    assert 0 < a.result < v["distance"]
    total = a.result / v["slow"]
    assert v["distance"] / v["fast"] < total < 2 * v["distance"] / v["fast"]
    assert v["slow"] * total + v["fast"] * total == 2 * v["distance"]
    html = plan(case).solution_html
    sections = BeautifulSoup(html, "html.parser").select(
        'section[data-content-kind="solution"]'
    )
    assert len(sections) == 4
    assert "Комментарий" in sections[2].get_text()
    assert "Приведём ещё одно решение" in sections[3].get_text()
    assert "Отразим путь" in sections[3].get_text()
    expected = "=" + math_common.number(a.result)
    for section in sections:
        assert any(
            expected in tag["data-inline-latex"]
            for tag in section.select("[data-inline-latex]")
        )
    first_distance = v["slow"] * v["distance"] / v["fast"]
    remaining = v["distance"] - first_distance
    assert first_distance + v["slow"] * remaining / (v["slow"] + v["fast"]) == a.result


def test_intermediate_speed_is_not_returned_instead_of_requested_train_speed():
    _, a = model.calculate(case_for("635151")["context"])
    assert a.root == 36 and a.result == 40
    half = a.question.values["distance"] / 2
    assert half / a.root - half / a.result == 1
    assert "36+4=40" in plan(case_for("635151")).solution_html


def test_catching_source_algebra_and_negative_root_typos_are_corrected():
    case = case_for("99594")
    _, a = model.calculate(case["context"])
    assert set(a.roots) == {sp.Integer(1), -sp.Rational(5, 12)}
    assert model.alternate(a.question).root == 60
    html = plan(case).solution_html
    assert r"\frac{t+0{,}5}{2t+0{,}5}" in html
    assert r"-\frac{5}{12}" in html.replace(" ", "")
    assert r"-\frac{2}{12}" not in html


def test_zero_saved_slope_answer_is_repaired_by_positive_distances():
    case = case_for("323899")
    context = deepcopy(case["context"])
    saved = next(
        s["html"]
        for s in context["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    assert BeautifulSoup(saved, "html.parser").get_text() == "000"
    result = plan(case, context)
    assert result.answer == "5"
    assert 7 * 5 + 7 * (5 - 3) == 49
    assert context == case["context"]


@pytest.mark.parametrize(
    "task,old,new,error",
    [
        ("99593", "750 метров", "0 метров", "positive distances"),
        ("99593", "каждую минуту", "каждую секунду", "complete road-motion"),
        ("99594", "30 минут", "0 минут", "positive duration"),
        ("99594", "повернул обратно", "продолжил движение", "complete road-motion"),
        ("99597", "2 часа 20 минут", "2 часа 20 секунд", "complete road-motion"),
        (
            "99597",
            "сначала он догнал второго",
            "сначала он догнал первого",
            "complete road-motion",
        ),
        ("323849", "3 км/ч", "2,5 км/ч", "second walker must be faster"),
        ("323849", "3 км/ч", "2 км/ч", "second walker must be faster"),
        ("323849", "со скоростью 3", "со скоростью 0", "positive distances"),
        ("323850", "5 часов", "1 час", "positive time for both"),
        ("323850", "5 часов", "30 минут", "positive time for both"),
        ("323850", "8 км", "3 км", "physical root"),
        ("323853", "50 минут", "220 минут", "positive riding time"),
        ("502291", "30-минутную", "140-минутную", "positive riding time"),
        ("635151", "на середине пути", "в конце пути", "complete road-motion"),
    ],
)
def test_nonphysical_times_speeds_and_changed_instructions_fail_closed(
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


@pytest.mark.parametrize(
    "task",
    ["99593", "99594", "99597", "323849", "323850", "323853", "502291", "635151"],
)
def test_unrequested_rounding_is_not_used_for_changed_distance_or_speed(task):
    _, a = model.calculate(case_for(task)["context"])
    values = dict(a.question.values)
    field = "first" if task == "99597" else "slow" if task == "323849" else "distance"
    values[field] += sp.Rational(1, 7)
    q = replace(a.question, values=values)
    with pytest.raises(ValueError, match="exact rational|non-terminating decimal"):
        changed = model.analyze(q)
        answer(changed.result)
