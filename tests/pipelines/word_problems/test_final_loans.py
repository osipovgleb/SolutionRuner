"""Finish the finance catalogue using the existing annual credit handlers."""

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
from solution_runner.pipelines.word_problems import annuity_credit, partial_credit
from solution_runner.pipelines.word_problems.annuity_questions import (
    parse as annuity_question,
)
from solution_runner.pipelines.word_problems.math_common import read
from solution_runner.pipelines.word_problems.partial_credit_questions import (
    parse as annual_question,
)

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_13_final_loans.json").read_text()
)
CASES = DATA["cases"]


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


def analysis(c):
    text = read(c["context"])[3]
    return (
        partial_credit.analyze(annual_question(text))
        if c["group"] == "517574"
        else annuity_credit.analyze(annuity_question(text))
    )


def changed(task, old, new):
    c = case_for(task)
    context = deepcopy(c["context"])
    text = read(context)[3]
    assert old in text
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + escape(text.replace(old, new)) + "</p>"
    return plan(c, context)


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_final_groups_reuse_two_existing_handlers(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == (
        "word-partial-credit" if g["key"] == "517574" else "word-annuity-credit"
    )
    assert p.source_group_id == g["uuid"] and p.snapshot_theme_id == g["theme_uuid"]
    assert (
        p.group_order_index == g["order"]
        and p.theme_order_index == 1
        and p.category_key == "13"
    )
    assert p.existing_solution_policy == "rewrite"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_all_sources_compute_independently_and_replay_without_mutation(c):
    verify_source(c)
    context = deepcopy(c["context"])
    original = plan(c)
    for s in context["normalized_content"]["sections"]:
        if s["key"] in {"answer", "solution"}:
            s["html"] = "<p>999999999</p>"
    result = plan(c, context)
    assert (
        result.answer == original.answer
        and result.solution_html == original.solution_html
    )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_independent_payment_loops_and_economic_constraints(c):
    a = analysis(c)
    q = a.question
    if c["group"] == "517574":
        payments = (a.payment, a.last)
        assert (q.capital * a.factor - q.payment) * a.factor - q.last == 0
        assert a.result == 100 * (a.factor - 1) and a.factor > 1
        assert len(a.roots) == 2 and a.roots[0] < 0 < a.roots[1]
        assert all(q.capital * r * r - q.payment * r - q.last == 0 for r in a.roots)
    else:
        interest = a.capital * q.rate / 100
        payments = (interest,) * 3 + (a.payment,) * 2
        assert a.payment - interest == a.capital / (a.factor + 1)
        assert a.result == (a.payment - interest) * q.scale
        assert a.debts[:4] == (a.capital,) * 4
    debt = a.capital
    for j, p in enumerate(payments, 1):
        debt = debt * a.factor - p
        assert debt == a.debts[j]
    assert debt == 0 and all(d > 0 for d in a.debts[:-1])
    assert sum(p / a.factor**j for j, p in enumerate(payments, 1)) == a.capital


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_parent_quadratic_method_and_five_year_table_are_preserved(c):
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    a = analysis(c)
    assert len(soup.select('section[data-content-kind="solution"]')) == 1
    assert not soup.select("img")
    tables = soup.select("table")
    if c["group"] == "517574":
        assert not tables
        assert (
            "квадратное уравнение" in soup.text and "Отрицательный корень" in soup.text
        )
        assert "b_1=" in str(soup) and "b_2=" in str(soup)
    else:
        assert len(tables) == 1
        rows = tables[0].select("tr")
        assert len(rows) == 7 and all(len(r.select("th,td")) == 4 for r in rows)
        assert [r.select("td")[0].text for r in rows[1:]] == [
            str(a.question.year + j) for j in range(6)
        ]
        assert all(
            r.select("td")[-1].span["data-inline-latex"] == "S" for r in rows[2:5]
        )
        assert rows[-1].select("td")[-1].span["data-inline-latex"] == "0"
        unit = "млн руб." if c["task"] == "630110" else "тыс. руб."
        assert all(unit in cell.text for cell in rows[0].select("th")[1:])
    assert len(soup.select("[data-inline-latex]")) >= 8


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unrecognized_instructions_and_assets_are_rejected(c, mode):
    verify_rejection(c, mode)


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("517574", "130 000", "50 000"),
        ("517574", "130 000", "40 000"),
        ("517574", "150 000", "150 001"),
        ("517574", "200 000", "0"),
        ("517574", "за два года", "за три года"),
        ("517574", "каждый январь", "каждый июль"),
        ("507275", "затем Валерий", "перед этим Валерий"),
        ("507275", "Валерию", "Борису"),
        ("630110", "2027, 2028 и 2029", "2027, 2028 и 2030"),
        ("630110", "2030 и 2031", "2029 и 2031"),
        ("630110", "к июлю 2031", "к июлю 2032"),
        ("630110", "остается равен 3,3", "остается равен 3,2"),
        ("630110", "на 20%", "на 0%"),
        ("630111", "1050 тыс. руб.", "1050 млн руб."),
    ],
)
def test_invalid_rates_timing_borrower_and_preserved_principal_are_rejected(
    task, old, new
):
    with pytest.raises(ValueError):
        changed(task, old, new)


def test_explicit_units_override_the_input_unit_of_a_grace_loan():
    r = changed(
        "660454",
        "Найдите разницу между первым и последним платежами.",
        "Сколько млн рублей составит разница между первым и последним платежами.",
    )
    assert r.answer == "0,24"


def test_equivalent_units_for_the_preserved_principal_are_accepted():
    r = changed(
        "630110", "остается равен 3,3 млн руб.", "остается равен 3300 тыс. руб."
    )
    assert r.answer == "1,5"


def test_fractional_interest_rate_is_recovered_exactly():
    c = case_for("517574")
    text = (
        read(c["context"])[3]
        .replace("200 000", "64 000")
        .replace("130 000", "32 000")
        .replace("150 000", "45 000")
    )
    a = partial_credit.analyze(annual_question(text))
    assert a.factor == sp.Rational(9, 8) and a.result == sp.Rational(25, 2)


def test_corrupt_answers_have_independent_and_unit_annotated_corrections():
    overrides = {c["task"]: c for c in CASES if "expected_answer" in c}
    assert {key: c["expected_answer"] for key, c in overrides.items()} == {
        "517575": "20",
        "548489": "30",
        "630111": "500000",
        "660454": "240",
    }
    assert all(c["source_answer_note"] for c in overrides.values())
    assert (
        "https://ege.sdamgia.ru/problem?id=660454"
        in overrides["660454"]["source_answer_note"]
    )


def test_million_input_is_converted_to_an_explicit_ruble_answer():
    result = changed(
        "630110",
        "Сколько млн рублей составит разница между первым и последним платежами.",
        "На сколько рублей последняя выплата будет больше первой?",
    )
    assert result.answer == "1500000"
    assert r"1500000\text{ руб.}" in result.solution_html
