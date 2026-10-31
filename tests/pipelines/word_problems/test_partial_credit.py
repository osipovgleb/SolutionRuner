"""Three-year loan equations, parent tables, unit conventions and rejected timing."""

import json
from copy import deepcopy
from html import escape
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from test_profile_percentages import plan
from test_profile_percentages import (
    test_source_answer_is_computed_without_mutation_and_replay_has_no_more_changes as verify_source,
)
from test_profile_percentages import (
    test_unknown_instructions_and_assets_fail_closed as verify_rejection,
)

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.word_problems import partial_credit as model
from solution_runner.pipelines.word_problems.loan_schedule import balances
from solution_runner.pipelines.word_problems.math_common import read
from solution_runner.pipelines.word_problems.partial_credit_questions import parse

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_13_partial_credit.json").read_text()
)
CASES = DATA["cases"]


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


def changed(task, old, new):
    c = case_for(task)
    context = deepcopy(c["context"])
    text = read(context)[3]
    assert old in text
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + escape(text.replace(old, new)) + "</p>"
    return plan(c, context)


def analysis(c):
    return model.analyze(parse(read(c["context"])[3]))


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_six_groups_share_the_same_credit_equation(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "word-partial-credit"
    assert p.source_group_id == g["uuid"] and p.snapshot_theme_id == g["theme_uuid"]
    assert p.group_order_index == g["order"] and p.theme_order_index == 1
    assert p.category_key == "13" and p.existing_solution_policy == "rewrite"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_sources_compute_answers_without_mutation_and_replay_cleanly(c):
    verify_source(c)
    original = plan(c)
    context = deepcopy(c["context"])
    for s in context["normalized_content"]["sections"]:
        if s["key"] in {"answer", "solution"}:
            s["html"] = "<p>999999999</p>"
    result = plan(c, context)
    assert (
        result.answer == original.answer
        and result.solution_html == original.solution_html
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_independent_cash_flows_and_successive_years(c):
    a = analysis(c)
    payments = (a.payment, a.payment, a.last)
    discounted = sum(p / a.factor**j for j, p in enumerate(payments, 1))
    assert discounted == a.capital
    debt = a.capital
    for j, p in enumerate(payments, 1):
        debt = debt + debt * a.question.rate / 100 - p
        assert debt == a.debts[j]
    assert debt == 0 and all(d > 0 for d in a.debts[:-1])
    assert sum(payments) == a.total
    if a.question.total is not None:
        assert a.total == a.question.total
    if a.question.last is not None:
        assert a.last == a.question.last
    expected = {
        "first": a.payment,
        "last": a.last,
        "capital": a.capital,
        "total": a.total,
    }[a.question.target]
    assert a.result == expected * a.question.scale


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_parent_table_and_sequential_method_are_preserved(c):
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    assert len(soup.select('section[data-content-kind="solution"]')) == 1
    tables = soup.select("table")
    assert len(tables) == (1 if c["group"] == "630122" else 0)
    assert not soup.select("img")
    if tables:
        rows = tables[0].select("tr")
        assert len(rows) == 5 and all(len(r.select("td,th")) == 4 for r in rows)
        assert [r.select("td")[0].text for r in rows[1:]] == [
            "2026",
            "2027",
            "2028",
            "2029",
        ]
        assert rows[-1].select("td")[-1].span["data-inline-latex"] == "0"
        expected = (
            "560{,}1-2x"
            if c["task"] == "630187"
            else ("833{,}8" if c["task"] == "630122" else "499{,}2")
        )
        assert rows[-1].select("td")[2].span["data-inline-latex"] == expected
    else:
        text = soup.get_text()
        assert "2027" in text and "2028" in text and "2029" in text
        assert len(soup.select("[data-inline-latex]")) >= 6


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unknown_instructions_or_figures_are_rejected(c, mode):
    verify_rejection(c, mode)


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("630122", "платеж в 2029", "платеж в 2030"),
        ("630122", "к июлю 2029", "к июлю 2030"),
        ("630122", "в 2027 и 2028", "в 2027 и 2029"),
        (
            "630122",
            "Сколько рублей составит платеж в 2027",
            "Сколько рублей составит платеж в 2028",
        ),
        ("630122", "833,8", "1064,8"),
        ("630122", "833,8", "1200"),
        ("630129", "по 400", "по 900"),
        ("630129", "на 20%", "на 0%"),
        ("630129", "каждый январь", "каждый июль"),
        ("630187", "560,1", "659,1"),
        ("630187", "560,1", "800"),
        ("630197", "200 тыс. руб.", "0 тыс. руб."),
        ("630219", "будет равен 417,6", "будет равен 0"),
        ("672873", "в 2027 и в 2028", "в 2026 и в 2028"),
        ("697032", "равными", "неравными"),
    ],
)
def test_inconsistent_dates_timing_and_nonpositive_payments_fail_closed(task, old, new):
    with pytest.raises(ValueError):
        changed(task, old, new)


@pytest.mark.parametrize(
    "capital,factor,payments",
    [
        (100, 2, (201, 1)),
        (100, 2, (100, 100)),
        (0, 2, (100, 100)),
        (100, 1, (50, 50)),
        (100, 2, (0, 400)),
    ],
)
def test_shared_schedule_rejects_premature_or_incomplete_repayment(
    capital, factor, payments
):
    with pytest.raises(ValueError):
        balances(capital, factor, payments)


def test_parent_unit_conventions_are_retained_for_children_with_omitted_units():
    assert plan(case_for("630165")).answer == "813519,5"
    assert plan(case_for("630261")).answer == "634500"
    assert plan(case_for("672902")).answer == "900"
    assert plan(case_for("697052")).answer == "1049,6"


def test_corrupt_source_answers_have_documented_independent_corrections():
    overrides = {c["task"]: c for c in CASES if "expected_answer" in c}
    assert {task: c["expected_answer"] for task, c in overrides.items()} == {
        "630158": "400000",
        "630187": "100000",
        "630129": "953600",
        "630261": "634500",
        "672902": "900",
        "697052": "1049,6",
    }
    assert all(c["source_answer_note"] for c in overrides.values())


def test_explicit_ruble_output_overrides_the_parent_thousand_convention():
    result = changed(
        "697032",
        "Найдите сумму всех платежей после полного погашения кредита.",
        "Найдите сумму всех платежей после полного погашения кредита. Ответ дайте в рублях.",
    )
    assert result.answer == "1190400"
