"""Equal-principal balances, all parent methods, exact constraints and PDF reuse."""

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
from solution_runner.pipelines.word_problems import differentiated_credit as model
from solution_runner.pipelines.word_problems import loan_reference
from solution_runner.pipelines.word_problems.common import UnsupportedCondition
from solution_runner.pipelines.word_problems.differentiated_questions import parse

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_13_differentiated.json").read_text()
)
CASES = DATA["cases"]


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


def changed(task, old, new):
    case = case_for(task)
    context = deepcopy(case["context"])
    text = loan_reference.read(context)[2]
    assert old in text
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + escape(text.replace(old, new)) + "</p>"
    return context


def analysis(case):
    return model.analyze(parse(loan_reference.read(case["context"])[2]))


def solution(result):
    return BeautifulSoup(
        next(
            t["value"]["html"]
            for t in result.transformations
            if t["transformation_target_id"].startswith("section:solution")
        ),
        "html.parser",
    )


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_three_credit_profiles_share_one_registered_rule(group):
    p = get_group_profile(group["key"])
    assert p.content_rule_key == "word-differentiated-credit"
    assert (
        p.source_group_id == group["uuid"]
        and p.snapshot_theme_id == group["theme_uuid"]
    )
    assert p.group_order_index == group["order"] and p.theme_order_index == 1
    assert (
        p.category_key == "13"
        and p.catalog_snapshot_id == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_source_ignores_saved_answers_and_replays_without_more_changes(case):
    verify_source(case)
    context = deepcopy(case["context"])
    original = plan(case)
    for s in context["normalized_content"]["sections"]:
        if s["key"] in {"answer", "solution"}:
            s["html"] = "<p>999999999</p>"
    altered = plan(case, context)
    assert altered.answer == original.answer and solution(altered) == solution(original)
    assert all(
        t["transformation_target_id"].startswith(("section:answer", "section:solution"))
        for t in altered.transformations
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_parent_methods_are_kept_in_their_original_order(case):
    a = analysis(case)
    soup = solution(plan(case))
    methods = soup.select('section[data-content-kind="solution"]')
    assert len(methods) == (1 if a.question.kind == "rate_bound" else 2)
    assert all(len(m.select("[data-inline-latex]")) >= 5 for m in methods)
    if len(methods) == 2:
        assert methods[1]["data-solution-title"] == (
            "Приведём авторское решение."
            if a.question.kind == "maximum"
            else "Приведем другое решение."
        )
        assert "Долг в июле уменьшается равномерно" in methods[1].get_text()
        assert "арифметическая прогрессия" in methods[0].get_text()
        assert len(methods[0].select("a")) == 1 and not methods[1].select("a")
    assert not soup.select("img")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_independent_yearly_schedule_closes_the_debt_and_matches_total(case):
    a = analysis(case)
    s = a.question.capital
    d = s / a.periods
    i = a.rate / 100
    debt = s
    payments = []
    for _ in range(a.periods):
        payment = d + debt * i
        debt = debt * (1 + i) - payment
        payments.append(payment)
    assert debt == 0 and tuple(payments) == a.payments
    assert sum(payments) == a.total == s + i * s * (a.periods + 1) / 2
    assert payments[0] > payments[-1] or a.periods == 1
    if a.question.kind == "rate_bound":
        assert payments[-1] == a.question.target


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unknown_instructions_and_assets_are_not_ignored(case, mode):
    verify_rejection(case, mode)


@pytest.mark.parametrize(
    "task,expected,term",
    [
        ("517241", "15", 10),
        ("513108", "16,2", 15),
        ("513109", "26,35", 10),
        ("513107", "80,5", 14),
        ("517517", "4", 4),
        ("521918", "8", 8),
        ("526343", "10", 10),
    ],
)
def test_corrupt_source_answers_have_audited_expected_values(task, expected, term):
    case = case_for(task)
    a = analysis(case)
    assert case["expected_answer"] == expected and case["source_answer_note"]
    assert plan(case).answer == expected and a.periods == term


@pytest.mark.parametrize("task", ["517480", "517569"])
def test_original_general_pdf_is_reused_as_a_reference_without_asset_changes(task):
    case = case_for(task)
    before = deepcopy(case["context"])
    result = plan(case)
    assert case["context"] == before
    links = solution(result).select("a")
    assert len(links) == 1 and links[0]["data-asset-id"] == loan_reference.PDF
    assert (
        links[0]["data-asset-key"] == "attachment_1"
        and links[0]["href"] == "/assets/" + loan_reference.PDF
    )
    transform = next(
        t
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
    assert transform["value"]["asset_keys"] == ["attachment_1"]
    assert all(
        not t["transformation_target_id"].startswith("asset:")
        for t in result.transformations
    )


def test_child_without_attachment_uses_original_public_reference_without_new_asset():
    result = plan(case_for("513108"))
    links = solution(result).select("a")
    assert (
        len(links) == 1
        and links[0]["href"] == loan_reference.URL
        and "data-asset-key" not in links[0].attrs
    )
    assert (
        next(
            t
            for t in result.transformations
            if t["transformation_target_id"].startswith("section:solution")
        )["value"]["asset_keys"]
        == []
    )


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("517203", "на срок 10 лет", "на срок 0 лет"),
        ("517203", "0,819 млн", "0,6 млн"),
        ("517203", "не менее", "не более"),
        ("517480", "3,6 млн", "1,8 млн"),
        ("517480", "3,6 млн", "3,7 млн"),
        ("517480", "на 20%", "на 0%"),
        ("517480", "на одну и ту же сумму", "на разные суммы"),
        ("517569", "27 млн", "18 млн"),
        ("517569", "27 млн", "26 млн"),
        ("517569", "каждый январь", "каждый июль"),
    ],
)
def test_invalid_or_changed_repayment_data_fail_closed(task, old, new):
    with pytest.raises(UnsupportedCondition):
        plan(case_for(task), changed(task, old, new))


def test_rate_bound_is_not_rounded_to_a_whole_percent():
    context = changed("517203", "0,819 млн", "0,8225 млн")
    assert plan(case_for("517203"), context).answer == "17,5"


def test_positive_integral_one_year_term_is_allowed():
    context = changed("517480", "3,6 млн", "10,8 млн")
    result = plan(case_for("517480"), context)
    assert result.answer == "10,8"


def test_duplicate_or_condition_pdf_reference_is_rejected():
    case = case_for("517480")
    context = deepcopy(case["context"])
    context["normalized_content"]["assets"] *= 2
    with pytest.raises(UnsupportedCondition):
        plan(case, context)
    context = deepcopy(case["context"])
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["asset_keys"] = ["attachment_1"]
    with pytest.raises(UnsupportedCondition):
        plan(case, context)
