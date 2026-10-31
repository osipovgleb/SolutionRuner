"""Summed rates, remaining work, time units and all parent explanations."""

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
from solution_runner.pipelines.word_problems import work_rate_models as model
from solution_runner.pipelines.word_problems.motion_questions import duration
from solution_runner.pipelines.word_problems.time_balance import X
from solution_runner.pipelines.word_problems.work_sum_proof import horizon

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_11_work_combined.json").read_text()
)
CASES = DATA["cases"]


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


def changed(case, old, new):
    context = deepcopy(case["context"])
    text = math_common.read(context)[3]
    assert old in text
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + text.replace(old, new) + "</p>"
    return context


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_all_eleven_groups_extend_the_existing_work_rate_rule(group):
    verify_registration(group)
    assert group["rule"] == "word-work-rate-balance"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_sources_replay_without_saved_answer_dependency(case):
    verify_source(case)
    _, a = model.calculate(case["context"])
    assert a.balance.domain.contains(a.root) is sp.true
    assert all(d.subs(X, a.root) != 0 for d in a.balance.denominators)
    assert sp.simplify((a.balance.left - a.balance.right).subs(X, a.root)) == 0
    assert a.balance.output.subs(X, a.root) == a.result > 0


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unread_instructions_and_foreign_assets_cannot_be_ignored(case, mode):
    verify_rejection(case, mode)


@pytest.mark.parametrize(
    "case",
    [c for c in CASES if c["group"] in {"99614", "99615"}],
    ids=lambda c: c["task"],
)
def test_summed_rates_have_three_methods_in_parent_order_and_an_integer_horizon(case):
    _, a = model.calculate(case["context"])
    values = tuple(
        a.question.values[k] for k in ("t1", "t2", "t3") if k in a.question.values
    )
    assert 0 < a.result < min(values)
    assert a.result * sum(1 / t for t in values) == 1
    common = horizon(values)
    assert all((common / t).is_Integer for t in values)
    sections = BeautifulSoup(plan(case).solution_html, "html.parser").select(
        'section[data-content-kind="solution"]'
    )
    assert len(sections) == 3
    assert all("=" + math_common.number(a.result) in str(s) for s in sections)
    if case["group"] == "99615":
        assert "совместная производительность" in sections[0].get_text()
    else:
        assert "Производительности складываются" in sections[0].get_text()
    assert "кратному" in sections[2].get_text()


@pytest.mark.parametrize(
    "task,values,result",
    [
        ("118555", (19, 57, 76), 12),
        ("118559", (12, 14, 84), 6),
        ("118295", (60, 90, 108), 27),
    ],
)
def test_pump_hours_are_converted_to_minutes_before_summing_rates(task, values, result):
    _, a = model.calculate(case_for(task)["context"])
    assert tuple(a.question.values[k] for k in ("t1", "t2", "t3")) == values
    assert a.result == result


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["group"] == "99613"], ids=lambda c: c["task"]
)
def test_delayed_joining_keeps_both_methods_and_finishes_after_the_join(case):
    _, a = model.calculate(case["context"])
    solo, delay = a.question.values["solo"], a.question.values["delay"]
    assert delay < a.result < solo
    assert delay / solo + 2 * (a.result - delay) / solo == 1
    assert (
        len(
            BeautifulSoup(plan(case).solution_html, "html.parser").select(
                'section[data-content-kind="solution"]'
            )
        )
        == 2
    )


def test_known_individual_time_child_inside_difference_group_reuses_known_rate_model():
    _, a = model.calculate(case_for("513622")["context"])
    assert a.question.kind == "work_known_pipe"
    assert a.question.values["joint"] == sp.Rational(35, 6)
    assert a.question.values["known"] == 7
    assert a.result == 35
    assert (
        len(
            BeautifulSoup(plan(case_for("513622")).solution_html, "html.parser").select(
                'section[data-content-kind="solution"]'
            )
        )
        == 2
    )


@pytest.mark.parametrize(
    "task,known,asked",
    [("99617", "Маша", "Даша"), ("118605", "Настя", "Катя"), ("118731", "Таня", "Аня")],
)
def test_names_select_the_known_and_requested_gardener(task, known, asked):
    _, a = model.calculate(case_for(task)["context"])
    assert a.question.values["known_name"] == known
    assert a.question.values["asked_name"] == asked
    assert (
        1 / a.result + 1 / a.question.values["known"] == 1 / a.question.values["joint"]
    )
    assert (
        known in plan(case_for(task)).solution_html
        and asked in plan(case_for(task)).solution_html
    )


@pytest.mark.parametrize("task", ["26596", "39751", "39795", "39799"])
def test_all_four_ratio_methods_table_and_attribution_adapt_when_first_is_slower(task):
    case = case_for(task)
    _, a = model.calculate(case["context"])
    v = a.question.values
    ratio = v["span1"] / v["span2"]
    assert a.result == v["joint"] * (1 + ratio)
    assert 1 / a.result + ratio / a.result == 1 / v["joint"]
    soup = BeautifulSoup(plan(case).solution_html, "html.parser")
    sections = soup.select('section[data-content-kind="solution"]')
    assert len(sections) == 4
    assert len(sections[0].find("table").find_all("tr")) == 3
    assert "Павел Юкляев" in sections[3]["data-solution-title"]
    if ratio > 1:
        assert "Первый рабочий работает быстрее" not in sections[3].get_text()


@pytest.mark.parametrize("task", ["99619", "119153", "514184", "509420", "689013"])
def test_time_gap_roots_use_positive_rates_and_monotonic_uniqueness(task):
    case = case_for(task)
    _, a = model.calculate(case["context"])
    v = a.question.values
    other = (
        a.root - v["gap"] if a.question.kind == "work_gap_filter" else a.root + v["gap"]
    )
    assert other > 0
    assert 1 / a.root + 1 / other == 1 / v["joint"]
    html = plan(case).solution_html
    assert "строго убывает" in html and "единственно" in html
    assert any(
        tag["data-inline-latex"].startswith("f'(")
        and tag["data-inline-latex"].endswith("<0")
        for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    )


def test_filter_source_minus_sign_is_corrected_and_requested_time_is_not_first_time():
    _, a = model.calculate(case_for("509420")["context"])
    assert a.root == 75 and a.result == 50
    assert set(a.roots) == {10, 75}
    html = plan(case_for("509420")).solution_html
    assert r"\frac{1}{t}+\frac{1}{t-25}=\frac{1}{30}" in html
    assert "75-25=50" in html


def test_printer_retains_mikhail_babinchuk_quadratic_note():
    html = plan(case_for("689013")).solution_html
    assert "Михаила Бабинчука" in html
    assert "t^{2} - 14 t - 120=0" in html
    assert r"\left\{20;-6\right\}" in html


@pytest.mark.parametrize("task", ["672795", "672879"])
def test_apprentice_and_master_shares_sum_to_one_with_the_requested_start_delay(task):
    _, a = model.calculate(case_for(task)["context"])
    v = a.question.values
    master_time = a.root
    apprentice_time = a.result + master_time
    assert 0 < a.result < apprentice_time < v["apprentice"]
    assert apprentice_time / v["apprentice"] + master_time / v["master"] == 1
    assert apprentice_time / v["apprentice"] == v["ratio"] * master_time / v["master"]


def test_one_minute_accusative_and_measured_pump_wording_are_supported():
    assert duration("1 минуту").total == sp.Rational(1, 60)
    _, a = model.calculate(case_for("119469")["context"])
    assert a.question.values["t1"] == 1 and a.question.values["t2"] == 2
    assert a.result == 4


@pytest.mark.parametrize(
    "task,old,new,error",
    [
        ("99613", "3 часа после", "15 часов после", "join before completion"),
        ("99613", "3 часа после", "16 часов после", "join before completion"),
        ("99614", "12 часов", "0 часов", "positive duration"),
        ("99615", "1 час", "0 минут", "positive duration"),
        ("99617", "одна Маша —", "одна Даша —", "distinct named participants"),
        ("99617", "20 минут", "12 минут", "solo time must exceed"),
        ("99618", "6 часов", "3 часа", "solo time must exceed"),
        ("99619", "6 минут дольше", "6 минут быстрее", "complete work-rate"),
        ("99620", "25 литров", "0 литров", "positive work times"),
        ("26596", "за два дня", "за 0 дней", "positive work times"),
        (
            "689013",
            "на 10 минут быстрее",
            "на 10 минут медленнее",
            "complete work-rate",
        ),
        ("672795", "за 12 часов", "за 36 часов", "positive time gap"),
        ("672795", "в два раза", "в 1 раза", "positive time gap"),
    ],
)
def test_nonphysical_time_budgets_names_and_changed_comparisons_fail_closed(
    task, old, new, error
):
    case = case_for(task)
    with pytest.raises(ValueError, match=error):
        plan(case, changed(case, old, new))
