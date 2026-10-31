"""All progression sources, exact sums, whole task counts and annual profits."""

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

from solution_runner.pipelines.word_problems import arithmetic_progression as arithmetic
from solution_runner.pipelines.word_problems import compound_deposit, math_common

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_11_progressions.json").read_text()
)
CASES = DATA["cases"]
ARITHMETIC = [c for c in CASES if int(c["group"]) <= 99585]
GROWTH = [c for c in CASES if c not in ARITHMETIC]


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


def changed(task, old, new):
    case = case_for(task)
    context = deepcopy(case["context"])
    text = math_common.read(context)[3]
    assert old in text
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + text.replace(old, new) + "</p>"
    return context


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_seven_arithmetic_groups_share_one_rule_and_growth_extends_deposits(group):
    verify_registration(group)
    assert group["rule"] == (
        "word-arithmetic-progression"
        if int(group["key"]) <= 99585
        else "word-compound-deposit"
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_parent_and_child_replays_without_saved_answer_dependency(case):
    verify_source(case)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unread_instructions_and_assets_cannot_be_ignored(case, mode):
    verify_rejection(case, mode)


@pytest.mark.parametrize("case", ARITHMETIC, ids=lambda c: c["task"])
def test_exact_arithmetic_sequences_have_the_required_sum_and_requested_member(case):
    _, a = arithmetic.calculate(case["context"])
    v = a.question.values
    if a.difference is None:
        # The daily amounts are underdetermined; an increasing positive witness exists.
        first = v["end_sum"] / 4
        difference = v["end_sum"] / (2 * (a.days - 1))
        assert a.result == a.days >= 2
    else:
        first, difference = v["first"], a.difference
        assert a.result == first + (v["asked"] - 1) * difference
        assert a.last == first + (a.days - 1) * difference
    terms = [first + i * difference for i in range(int(a.days))]
    assert all(t > 0 for t in terms) and difference > 0
    assert sum(terms) == v["total"]
    assert terms[0] + terms[-1] == (v.get("end_sum") or first + a.last)
    if a.question.counted:
        assert all(t.is_Integer is True for t in terms)
    html = plan(case).solution_html
    assert "арифметическую прогрессию" in html
    assert "S_n=" in html


@pytest.mark.parametrize("case", GROWTH, ids=lambda c: c["task"])
def test_geometric_growth_matches_independent_year_by_year_reinvestment(case):
    _, a = compound_deposit.calculate(case["context"])
    finals = []
    for account in a.accounts:
        value = account.capital
        for _ in range(account.periods):
            value += value * account.rate / 100
        assert value == account.result
        finals.append(value)
    assert a.result == (finals[0] if len(finals) == 1 else abs(finals[0] - finals[1]))


@pytest.mark.parametrize(
    "task,name",
    [
        ("99581", "Вася"),
        ("110551", "Петя"),
        ("99585", "Вера"),
        ("111913", "Лена"),
        ("112205", "Ира"),
        ("111915", "Настя"),
    ],
)
def test_named_participants_are_adapted_in_the_same_parent_method(task, name):
    html = plan(case_for(task)).solution_html
    assert name in html
    if name != "Вася":
        assert "Вася" not in html
    if name != "Вера":
        assert "Вера" not in html


@pytest.mark.parametrize("task", ["99586", "112207", "112211", "112275"])
def test_profit_preserves_sequential_note_and_annual_profit_not_capital_note(task):
    _, a = compound_deposit.calculate(case_for(task)["context"])
    account = a.accounts[0]
    html = plan(case_for(task)).solution_html
    assert "геометрической прогрессии" in html
    assert "найти последовательно" in html
    assert "не нужно вычитать" in html
    assert account.name in html
    assert all(
        str(year) + r"\text{ год}" in html
        for year in range(account.start + 1, account.end + 1)
    )
    if task == "112211":
        assert "Бубликов" not in html


@pytest.mark.parametrize(
    "task,larger",
    [("99587", "Бета"), ("112277", "Альфа"), ("112397", "Бета"), ("112279", "Бета")],
)
def test_final_capital_difference_selects_the_actual_larger_company(task, larger):
    html = plan(case_for(task)).solution_html
    assert "Капитал компании «" + larger + "» больше" in html
    assert "остаётся в обороте" in html


def test_continuous_daily_distance_may_be_fractional_but_whole_task_counts_may_not():
    context = changed("99582", "120 километров", "121 километров")
    _, a = arithmetic.calculate(context)
    assert a.difference == sp.Rational(61, 15) and a.result == sp.Rational(272, 15)
    context = changed("99580", "500 метров", "501 метров")
    _, a = arithmetic.calculate(context)
    assert a.result == sp.Rational(486, 5)
    with pytest.raises(ValueError, match="integer daily counts"):
        arithmetic.calculate(changed("99581", "434 задачи", "435 задачи"))


@pytest.mark.parametrize(
    "task,old,new,error",
    [
        ("99579", "240 метров", "241 метров", "whole days"),
        ("99579", "240 метров", "30 метров", "two whole days"),
        ("99579", "60 метров", "0 метров", "positive daily"),
        ("99580", "10 дней", "1 день", "whole day counts"),
        ("99580", "10 дней", "10,5 дней", "whole day counts"),
        ("99580", "500 метров", "30 метров", "increase must be positive"),
        ("99580", "500 метров", "20 метров", "increase must be positive"),
        ("99581", "Васе надо", "Пете надо", "named participant"),
        (
            "99581",
            "решил Вася в последний",
            "решил Петя в последний",
            "complete arithmetic",
        ),
        ("99585", "Вере надо", "Лене надо", "named participant"),
        ("99585", "640 открыток", "641 открыток", "integer daily counts"),
        ("99585", "10 открыток", "10,5 открыток", "integer daily counts"),
        ("99582", "третий день", "седьмой день", "within the completed"),
        ("99583", "14 дней", "8 дней", "within the completed"),
        ("99583", "норму перевозки", "норму потребления", "complete arithmetic"),
        ("99586", "за 2003 год", "за 1999 год", "chronological"),
        ("99586", "на 300%", "на 0%", "annual increase"),
        ("99586", "заработал Бубликов", "заработал Коржов", "name must match"),
        ("112275", "прибыль Коржова", "прибыль Бубликова", "name must match"),
        ("99587", "2002 года", "2003 года", "reinvest starting"),
        ("99587", "2004 года", "2005 года", "reinvest starting"),
        ("99587", "концу 2006 года", "концу 2003 года", "chronological"),
        ("99587", "«Бета»", "«Альфа»", "distinct companies"),
        ("99587", "не изымалась", "изымалась", "complete compound"),
        (
            "99587",
            "прибыль, которая составляла",
            "прибыль, которая увеличивалась на",
            "complete compound",
        ),
    ],
)
def test_nonphysical_discrete_counts_wrong_years_roles_and_unread_models_fail_closed(
    task, old, new, error
):
    with pytest.raises(ValueError, match=error):
        plan(case_for(task), changed(task, old, new))
