"""The same job/rate time equation for faster workers and faster pipes."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
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
from solution_runner.pipelines.word_problems import work_rate_models as model
from solution_runner.pipelines.word_problems.time_balance import Balance, X, solve

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_11_work_rates.json").read_text()
)
CASES = DATA["cases"]


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


def changed(case, replacements):
    context = deepcopy(case["context"])
    text = math_common.read(context)[3]
    for old, new in replacements:
        assert old in text
        text = text.replace(old, new)
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + text + "</p>"
    return context


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_all_eight_groups_use_one_work_rate_rule(group):
    verify_registration(group)
    assert group["rule"] == "word-work-rate-balance"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_sources_replay_without_saved_answer_dependency(case):
    verify_source(case)
    _, a = model.calculate(case["context"])
    q, v = a.question, a.question.values
    slow, fast = (
        (a.result - v["gap"], a.result)
        if q.target_fast
        else (a.result, a.result + v["gap"])
    )
    assert 0 < slow < fast
    assert v["slow_amount"] / slow - v["fast_amount"] / fast == v["delay"]
    assert a.balance.domain.contains(a.root) is sp.true
    assert sp.simplify((a.balance.left - a.balance.right).subs(X, a.root)) == 0
    assert all(d.subs(X, a.root) != 0 for d in a.balance.denominators)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unread_instructions_and_foreign_assets_fail_closed(case, mode):
    verify_rejection(case, mode)


@pytest.mark.parametrize(
    "task,replacements,expected",
    [
        (
            "26592",
            [("изготавливает второй рабочий", "изготавливает первый рабочий")],
            11,
        ),
        ("26594", [("делает первый рабочий?", "делает второй рабочий?")], 22),
        (
            "26597",
            [
                ("пропускает первая труба, если", "пропускает вторая труба, если"),
                ("дольше, чем вторая труба?", "быстрее, чем первая труба?"),
            ],
            11,
        ),
    ],
)
def test_requested_rate_is_read_from_the_actual_question_instead_of_the_group(
    task, replacements, expected
):
    case = case_for(task)
    assert plan(case, changed(case, replacements)).answer == str(expected)


def test_a_child_in_the_equal_order_group_can_have_different_job_counts():
    case = case_for("513425")
    _, a = model.calculate(case["context"])
    assert a.question.values["fast_amount"] == 780
    assert a.question.values["slow_amount"] == 840
    assert a.result == 30
    assert sp.Rational(840, 28) - sp.Rational(780, 30) == 4


@pytest.mark.parametrize(
    "task,old,new,error",
    [
        ("26592", "110 деталей", "0 деталей", "positive job amounts"),
        ("26592", "1 деталь больше", "0 деталей больше", "positive job amounts"),
        ("26592", "1 час быстрее", "0 часов быстрее", "positive duration"),
        ("26592", "110 деталей", "111 деталей", "exact rational"),
        (
            "26593",
            "изготавливает первый рабочий",
            "изготавливает второй рабочий",
            "consistently identified",
        ),
        ("26594", "на 6 часов меньше", "на 6 часов больше", "complete work-rate"),
        ("26597", "1 минуту дольше", "0 минут дольше", "positive job amounts"),
        ("26597", "1 минуту дольше", "1 час дольше", "complete work-rate"),
        (
            "26597",
            "дольше, чем вторая",
            "быстрее, чем вторая",
            "consistently identified",
        ),
        (
            "26598",
            "быстрее, чем первая",
            "быстрее, чем вторая",
            "consistently identified",
        ),
        ("26600", "500 литров", "0 литров", "positive job amounts"),
    ],
)
def test_nonphysical_data_ambiguous_pronouns_changed_roles_and_units_fail_closed(
    task, old, new, error
):
    case = case_for(task)
    with pytest.raises(ValueError, match=error):
        plan(case, changed(case, [(old, new)]))


def test_worker_time_gap_in_minutes_is_converted_to_hours_exactly():
    case = case_for("26592")
    context = changed(case, [("1 час быстрее", "60 минут быстрее")])
    assert plan(case, context).answer == "10"
    assert r"\frac{60}{60}=1" in plan(case, context).solution_html


def test_the_shared_solver_preserves_original_poles_after_cancellation():
    # The apparent root x=1 is forbidden by the original denominator.
    b = Balance(X - 1, sp.Integer(0), sp.Interval.open(0, sp.oo), (X - 1,))
    with pytest.raises(ValueError, match="physical root"):
        solve(b)


def test_the_shared_solver_rejects_ambiguous_physical_roots():
    b = Balance((X - 1) * (X - 2), sp.Integer(0), sp.Interval.open(0, sp.oo), ())
    with pytest.raises(ValueError, match="physical root"):
        solve(b)


def test_explicit_integral_domain_is_applied_before_root_uniqueness():
    b = Balance(
        (X - 10) * (5 * X - 1),
        sp.Integer(0),
        sp.Intersection(sp.S.Integers, sp.Interval(1, sp.oo)),
        (),
        20 / X,
    )
    _, roots, root, result = solve(b)
    assert set(roots) == {10, sp.Rational(1, 5)}
    assert root == 10 and result == 2
