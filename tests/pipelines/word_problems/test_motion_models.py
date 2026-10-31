"""Road-motion source replay, time units, roles and root restrictions."""

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

from solution_runner.pipelines.word_problems import math_common
from solution_runner.pipelines.word_problems import motion_models as model
from solution_runner.pipelines.word_problems.motion_proof import proof
from solution_runner.pipelines.word_problems.motion_questions import duration

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_11_motion.json").read_text()
)
CASES = DATA["cases"]


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_one_time_balance_rule_is_registered_in_the_existing_domain(group):
    verify_registration(group)
    assert group["rule"] == "word-motion-time-balance"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_sources_compute_independently_and_replay_without_changes(case):
    verify_source(case)
    _, a = model.calculate(case["context"])
    assert a.balance.domain.contains(a.root) is sp.true
    assert sp.simplify((a.balance.left - a.balance.right).subs(model.X, a.root)) == 0
    assert all(d.subs(model.X, a.root) != 0 for d in a.balance.denominators)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unread_instructions_and_foreign_assets_fail_closed(case, mode):
    verify_rejection(case, mode)


@pytest.mark.parametrize(
    "text,hours,minutes,total",
    [
        ("час", 1, 0, 1),
        ("два часа", 2, 0, 2),
        ("4 часа 20 минут", 4, 20, sp.Rational(13, 3)),
        ("2 часа 40 минут", 2, 40, sp.Rational(8, 3)),
        ("48 минут", 0, 48, sp.Rational(4, 5)),
        ("50 минут", 0, 50, sp.Rational(5, 6)),
        ("1 час 20 минут", 1, 20, sp.Rational(4, 3)),
        ("2 часа 30 минут", 2, 30, sp.Rational(5, 2)),
    ],
)
def test_hours_and_minutes_are_exact_rationals(text, hours, minutes, total):
    result = duration(text)
    assert (result.hours, result.minutes, result.total) == (hours, minutes, total)


@pytest.mark.parametrize(
    "text", ["0 часов", "-1 час", "1 час -20 минут", "2 суток", "час и 5 секунд"]
)
def test_invalid_or_unread_time_units_fail_closed(text):
    with pytest.raises(ValueError):
        duration(text)


@pytest.mark.parametrize(
    "task,target_fast,expected",
    [
        ("26581", True, 10),
        ("39193", False, 9),
        ("26582", False, 7),
        ("26583", True, 16),
        ("525405", False, 60),
        ("26584", False, 8),
    ],
)
def test_actual_question_selects_direction_or_finish_order(task, target_fast, expected):
    _, a = model.calculate(case_for(task)["context"])
    assert a.question.target_fast is target_fast
    assert a.result == expected
    distance, gap = (a.question.values[k] for k in ("distance", "gap"))
    slow, fast = (
        (expected - gap, expected) if target_fast else (expected, expected + gap)
    )
    assert slow > 0 and fast > slow
    assert distance / slow - distance / fast == a.question.durations["delay"].total


@pytest.mark.parametrize(
    "minimum,expected", [(48, 52), (39, 52), (52, None), (38, None), (0, None)]
)
def test_strict_lower_bound_selects_one_root_and_never_guesses(minimum, expected):
    _, source = model.calculate(case_for("26579")["context"])
    q = replace(
        source.question,
        values={**source.question.values, "minimum": sp.Integer(minimum)},
    )
    if expected is None:
        with pytest.raises(ValueError, match="one exact rational physical root"):
            model.analyze(q)
    else:
        a = model.analyze(q)
        assert set(a.roots) == {39, 52} and a.result == expected


@pytest.mark.parametrize(
    "task,old,new,error",
    [
        ("26578", "24 км/ч", "25 км/ч", "exact rational"),
        ("26580", "75 км", "0 км", "positive distances"),
        ("26580", "6 часов", "0 часов", "positive duration"),
        ("99589", "180 км", "330 км", "strictly between"),
        ("99590", "435 км", "50 км", "second car must start"),
        ("99591", "350 км", "480 км", "strictly between"),
        ("26579", "больше 48", "не меньше 48", "complete road-motion"),
        ("26581", "из B в A. Ответ", "из A в A. Ответ", "complete road-motion"),
        ("26583", "на 1 час раньше", "на 1 час позже", "complete road-motion"),
        ("99592", "48 минут", "48 секунд", "complete road-motion"),
    ],
)
def test_changed_physics_units_and_nonrational_answers_fail_closed(
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
    "task,first,second,average",
    [
        ("26579", 39, 78, 52),
        ("39063", 60, 84, 70),
        ("39089", 45, 105, 63),
        ("39097", 42, 56, 48),
    ],
)
def test_parent_harmonic_mean_note_is_adapted_to_both_half_speeds(
    task, first, second, average
):
    _, a = model.calculate(case_for(task)["context"])
    html = proof(a)
    assert "Примечание" in html and "среднее арифметическое" in html
    assert f"t_1=\\frac{{z}}{{{first}}}" in html
    assert f"t_2=\\frac{{z}}{{{second}}}" in html
    assert sp.Rational(2 * first * second, first + second) == average == a.result


@pytest.mark.parametrize("task", ["99592", "113101", "519512", "519538"])
def test_meeting_precedes_both_arrivals_and_total_time_pole_is_excluded(task):
    _, a = model.calculate(case_for(task)["context"])
    delay = a.question.durations["delay"].total
    meet = a.question.durations["meeting"].total
    assert 0 < meet < a.result - delay < a.result
    assert meet / a.result + meet / (a.result - delay) == 1
    assert all(not a.balance.domain.contains(r) for r in a.roots if r != a.root)
