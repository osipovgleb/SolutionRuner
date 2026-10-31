"""Annual deposit schedules retain exact money, timing, units and parent methods."""

import json
from copy import deepcopy
from html import escape
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_profile_percentages import plan
from test_profile_percentages import (
    test_source_answer_is_computed_without_mutation_and_replay_has_no_more_changes as verify_source,
)
from test_profile_percentages import (
    test_unknown_instructions_and_assets_fail_closed as verify_rejection,
)

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.word_problems import (
    compound_deposit,
    deposit_schedules,
    math_common,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_13_deposits.json").read_text()
)
CASES = DATA["cases"]


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


def changed(task, old, new):
    case = case_for(task)
    context = deepcopy(case["context"])
    text = math_common.read(context)[3]
    assert old in text
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + escape(text.replace(old, new)) + "</p>"
    return context


def solution(result):
    return BeautifulSoup(
        next(
            t["value"]["html"]
            for t in result.transformations
            if t["transformation_target_id"] == "section:solution:1"
        ),
        "html.parser",
    )


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_five_financial_profiles_extend_existing_compound_deposit_handler(group):
    p = get_group_profile(group["key"])
    assert p.content_rule_key == "word-compound-deposit"
    assert (
        p.source_group_id == group["uuid"]
        and p.snapshot_theme_id == group["theme_uuid"]
    )
    assert (
        p.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
        and p.category_key == "13"
    )
    assert p.group_order_index == group["order"] and p.theme_order_index == 0


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_sources_compute_without_saved_answers_and_replay_is_idempotent(case):
    verify_source(case)
    context = deepcopy(case["context"])
    original = plan(case)
    for s in context["normalized_content"]["sections"]:
        if s["key"] in {"answer", "solution"}:
            s["html"] = "<p>999999999</p>"
    result = plan(case, context)
    assert result.answer == original.answer and solution(result) == solution(original)
    assert {t["transformation_target_id"] for t in result.transformations} <= {
        "section:answer:1",
        "section:solution:1",
    }
    _, a = compound_deposit.calculate(case["context"])
    assert all(v.is_Rational for v in a.balances)
    assert len(a.balances) == a.question.periods
    soup = solution(original)
    assert not soup.select("img") and len(soup.select("[data-inline-latex]")) >= 5


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unknown_instructions_or_assets_are_not_ignored(case, mode):
    verify_rejection(case, mode)


def test_beginning_of_next_year_cash_flow_precedes_that_years_interest():
    case = case_for("704682")
    _, a = compound_deposit.calculate(case["context"])
    assert a.balances == (sp.Integer(138), sp.Rational("170.2"), sp.Rational("207.23"))


def test_withdrawal_and_ruble_conversion_are_exact():
    _, a = compound_deposit.calculate(case_for("704683")["context"])
    assert a.question.flow == -5 and a.balances[-1] == sp.Rational("128.205")
    assert a.result == 128205
    assert "128{,}205" in str(solution(plan(case_for("704683"))))


def test_initial_amount_and_rate_reproduce_the_stated_final_deposit():
    _, a = compound_deposit.calculate(case_for("704684")["context"])
    assert a.capital == 85 and a.balances[-1] == sp.Rational("173.28")
    _, b = compound_deposit.calculate(case_for("704685")["context"])
    assert b.rate == 10 and b.capital * (1 + b.rate / 100) ** 3 == sp.Rational("665.5")


def test_comparison_reports_larger_variant_and_converts_difference_to_rubles():
    case = case_for("704686")
    _, a = compound_deposit.calculate(case["context"])
    assert (
        a.balances[-1] == 1331
        and a.alternative[-1] == sp.Rational("1330.56")
        and a.result == 440
    )
    assert "при первом варианте" in solution(plan(case)).get_text()
    context = changed("704686", "составляет 8%", "составляет 10%")
    result = plan(case, context)
    assert (
        result.answer == "73480"
        and "при втором варианте" in solution(result).get_text()
    )


@pytest.mark.parametrize(
    "task,old,new,expected",
    [
        ("704682", "на 15%", "на 0%", "140"),
        ("704682", "120 миллионов", "240 миллионов", "389,735"),
        ("704683", "Ответ дайте в рублях", "Ответ дайте в тысячах рублей", "128,205"),
        ("704684", "173,28 тысяч", "190,56 тысяч", "95"),
        ("704685", "665,5 тысяч", "864 тысяч", "20"),
    ],
)
def test_actual_numbers_and_requested_units_drive_recalculation(
    task, old, new, expected
):
    assert plan(case_for(task), changed(task, old, new)).answer == expected


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("704682", "начиная со второго", "начиная с первого"),
        ("704682", "В конце каждого года", "В начале каждого года"),
        ("704682", "третьего года размещения", "четвертого года размещения"),
        ("704682", "15%", "-15%"),
        ("704683", "снимается 5 тысяч", "снимается 500 тысяч"),
        ("704684", "второго и третьего", "первого и третьего"),
        ("704684", "173,28 тысяч", "1 тысяч"),
        ("704685", "665,5 тысяч", "666 тысяч"),
        ("704685", "665,5 тысяч", "400 тысяч"),
        ("704686", "увеличивается на 2%", "увеличивается на -2%"),
    ],
)
def test_changed_timing_invalid_data_and_inexact_rate_fail_closed(task, old, new):
    with pytest.raises(ValueError):
        plan(case_for(task), changed(task, old, new))


def test_equal_comparison_does_not_invent_a_larger_variant():
    context = changed("704686", "составляет 8%", "составляет 10%")
    text = math_common.read(context)[3].replace(
        "увеличивается на 2%", "увеличивается на 0%"
    )
    with pytest.raises(UnsupportedCondition):
        deposit_schedules.analyze(text)


def test_schedule_beyond_supported_term_is_not_partially_parsed():
    text = math_common.read(case_for("704682")["context"])[3].replace(
        "— 3 года", "— 30 лет"
    )
    with pytest.raises(UnsupportedCondition):
        deposit_schedules.analyze(text)


def test_one_year_deposit_has_no_future_cash_flow():
    case = case_for("704682")
    text = (
        math_common.read(case["context"])[3]
        .replace("— 3 года", "— 1 год")
        .replace("третьего года размещения", "первого года размещения")
    )
    context = deepcopy(case["context"])
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + escape(text) + "</p>"
    result = plan(case, context)
    assert result.answer == "138"
    assert "j=2" not in str(solution(result))
