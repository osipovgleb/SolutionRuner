"""Exact annual balances, retained parent methods and fail-closed credit timing."""

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
from solution_runner.pipelines.word_problems import annuity_credit as model
from solution_runner.pipelines.word_problems.annuity_questions import parse
from solution_runner.pipelines.word_problems.math_common import read

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_13_annuity.json").read_text()
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


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_five_groups_share_one_annuity_handler(group):
    p = get_group_profile(group["key"])
    assert p.content_rule_key == "word-annuity-credit"
    assert (
        p.source_group_id == group["uuid"]
        and p.snapshot_theme_id == group["theme_uuid"]
    )
    assert p.group_order_index == group["order"] and p.theme_order_index == 1
    assert p.category_key == "13" and p.existing_solution_policy == "rewrite"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_sources_are_computed_without_mutation_or_saved_answer_dependency(c):
    verify_source(c)
    context = deepcopy(c["context"])
    original = plan(c)
    for s in context["normalized_content"]["sections"]:
        if s["key"] in {"answer", "solution"}:
            s["html"] = "<p>99999999</p>"
    result = plan(c, context)
    assert (
        result.answer == original.answer
        and result.solution_html == original.solution_html
    )
    assert not context["normalized_content"]["assets"]


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_independent_discounted_cash_flow_and_yearly_balance(c):
    a = analysis(c)
    discounted = sum(a.payment / a.factor**j for j in range(1, a.question.periods + 1))
    assert discounted == a.capital
    debt = a.capital
    for j in range(a.question.periods):
        debt += debt * a.question.rate / 100
        debt -= a.payment
        assert debt == a.debts[j + 1]
    assert debt == 0
    if a.question.style == "refinance":
        new_final = a.debts[1] * (1 + a.question.new_rate / 100)
        assert 2 * a.payment - (a.payment + new_final) == a.result
    elif a.question.style == "principal":
        assert a.result == a.capital * 1_000_000
    else:
        assert a.result == a.question.periods * a.payment


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_original_methods_and_table_are_preserved(c):
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    methods = soup.select('section[data-content-kind="solution"]')
    assert len(methods) == (2 if c["group"] == "517503" else 1)
    if len(methods) == 2:
        assert methods[1]["data-solution-title"] == "Приведём решение в общем случае."
        assert "S_2=Sb^2-(1+b)X=0" in str(methods[1])
    tables = soup.select("table")
    assert len(tables) == (1 if c["group"] == "704627" else 0)
    assert not soup.select("img")
    assert all(len(m.select("[data-inline-latex]")) >= 5 for m in methods)
    if tables:
        rows = tables[0].select("tr")
        assert len(rows) == 5 and all(len(r.select("th,td")) == 4 for r in rows)
        assert [r.select("td")[0].text for r in rows[1:]] == [
            "2030",
            "2031",
            "2032",
            "2033",
        ]
        assert (
            rows[-1].select("td")[-1].span["data-inline-latex"] == "1{,}728S-3{,}64x=0"
        )


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unknown_instructions_and_assets_fail_closed(c, mode):
    verify_rejection(c, mode)


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("517503", "на 10%", "на 0%"),
        ("517503", "147 000", "0"),
        ("517503", "двумя равными", "двумя неравными"),
        ("517503", "каждый январь", "каждый июль"),
        ("548482", "после чего происходит платеж", "перед чем происходит платеж"),
        ("628752", "2,662 млн", "0 млн"),
        ("628752", "на три года", "на четыре года"),
        ("561179", "до 7%", "до 10%"),
        ("561179", "до 7%", "до 11%"),
        ("561179", "феврале 2021", "феврале 2023"),
        ("561179", "В январе 2020", "В январе 2019"),
        ("561179", "Борис сделал", "Василий сделал"),
        ("704627", "тремя равными", "четырьмя равными"),
    ],
)
def test_invalid_amounts_timing_recipients_and_refinancing_are_rejected(task, old, new):
    with pytest.raises(ValueError):
        changed(task, old, new)


def test_zero_final_year_interest_is_valid_after_refinancing():
    result = changed("561179", "до 7%", "до 0%")
    assert result.answer == "220000"


def test_fractional_rate_is_used_exactly_without_money_rounding():
    text = read(case_for("517503")["context"])[3].replace("на 10%", "на 12,5%")
    a = model.analyze(parse(text))
    assert a.result == sp.Rational(2 * 147000) * sp.Rational(9, 8) ** 2 / (
        sp.Rational(9, 8) + 1
    )
    with pytest.raises(ValueError, match="non-terminating"):
        changed("517503", "на 10%", "на 12,5%")
    c = case_for("517503")
    context = deepcopy(c["context"])
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + escape(text.replace("147 000", "136 000")) + "</p>"
    assert plan(c, context).answer == "162000"


def test_corrupt_source_placeholders_have_explicit_independent_corrections():
    overrides = {c["task"]: c for c in CASES if "expected_answer" in c}
    assert {k: v["expected_answer"] for k, v in overrides.items()} == {
        "548482": "720000",
        "628778": "5460000",
    }
    assert all(v["source_answer_note"] for v in overrides.values())
