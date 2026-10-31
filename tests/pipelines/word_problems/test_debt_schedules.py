"""Read complete debt tables and verify exact integer bounds and parent methods."""

import json
from copy import deepcopy
from dataclasses import replace
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
from solution_runner.pipelines.word_problems import debt_schedule as model
from solution_runner.pipelines.word_problems.debt_schedule_questions import parse
from solution_runner.pipelines.word_problems.debt_table_reader import read

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_13_debt_schedules.json").read_text()
)
CASES = DATA["cases"]


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


def analysis(c):
    data = read(c["context"])
    return model.analyze(parse(data[3], data[4]))


def edited(task, edit):
    c = case_for(task)
    context = deepcopy(c["context"])
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    edit(soup)
    condition["html"] = str(soup)
    return plan(c, context)


def changed(task, old, new):
    c = case_for(task)
    condition = next(
        s
        for s in c["context"]["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    assert old in condition["html"]
    context = deepcopy(c["context"])
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = condition["html"].replace(old, new)
    return plan(c, context)


@pytest.mark.parametrize("g", DATA["groups"], ids=lambda g: g["key"])
def test_seven_profiles_share_one_prescribed_schedule(g):
    p = get_group_profile(g["key"])
    assert p.content_rule_key == "word-debt-schedule"
    assert p.source_group_id == g["uuid"] and p.snapshot_theme_id == g["theme_uuid"]
    assert (
        p.group_order_index == g["order"]
        and p.theme_order_index == 1
        and p.category_key == "13"
    )
    assert p.existing_solution_policy == "rewrite"


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_sources_ignore_saved_answers_and_replay_without_mutating_conditions(c):
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


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_payments_match_independent_interest_sum_and_debt_progression(c):
    a = analysis(c)
    q = a.question
    interest = q.rate / 100 * sum(q.ratios[:-1])
    assert sum(a.payments) == 1 + interest
    debt = sp.Integer(1)
    for payment, expected in zip(a.payments, q.ratios[1:]):
        debt += debt * q.rate / 100
        debt -= payment
        assert debt == expected
    assert debt == 0
    if q.kind == "geometric":
        assert a.result * a.total == q.limit
    elif q.kind == "monthly":
        assert a.result == interest * 100
    else:
        satisfying = [
            s
            for s in range(1, int(a.result) + 3)
            if model.satisfies(q, a.coefficient, s)
        ]
        assert (
            max(satisfying) if q.extreme == "наибольшее" else min(satisfying)
        ) == a.result


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
def test_parent_table_or_enumerated_payments_are_retained(c):
    a = analysis(c)
    q = a.question
    soup = BeautifulSoup(plan(c).solution_html, "html.parser")
    assert len(soup.select('section[data-content-kind="solution"]')) == 1
    tables = soup.select("table")
    enumerated = (
        q.kind == "bound" and q.scope == "каждая из выплат" and q.unit == "тыс. руб."
    )
    assert len(tables) == (0 if enumerated else 1)
    assert not soup.select("img")
    if tables:
        rows = tables[0].select("tr")
        if q.kind == "monthly":
            assert len(rows) == 5 and all(len(r.select("td,th")) == 7 for r in rows)
            assert [cell.text for cell in rows[0].select("th")][1:] == [
                "14.02",
                "14.03",
                "14.04",
                "14.05",
                "14.06",
                "14.07",
            ]
        else:
            assert len(rows) == len(q.ratios) + 1 and all(
                len(r.select("td,th")) == 4 for r in rows
            )
            assert [r.select("td")[0].text for r in rows[1:]] == [
                str(q.year + j) for j in range(len(q.ratios))
            ]
            if q.kind == "geometric":
                assert all(
                    "+" in r.select("td")[2].span["data-inline-latex"] for r in rows[2:]
                )
    else:
        assert "P_1" in str(soup) and "P_2" in str(soup) and "P_3" in str(soup)


@pytest.mark.parametrize("c", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unrecognized_instructions_and_assets_are_rejected(c, mode):
    verify_rejection(c, mode)


@pytest.mark.parametrize(
    "relation,extreme,limit,expected",
    [
        ("меньше", "наибольшее", 28, 49),
        ("не больше", "наибольшее", 28, 50),
        ("больше", "наименьшее", 20, 51),
        ("не меньше", "наименьшее", 20, 50),
        ("меньше", "наибольшее", sp.Rational(281, 10), 50),
        ("не больше", "наибольшее", sp.Rational(281, 10), 50),
        ("больше", "наименьшее", sp.Rational(201, 10), 51),
        ("не меньше", "наименьшее", sp.Rational(201, 10), 51),
    ],
)
def test_all_strict_and_inclusive_integer_payment_boundaries(
    relation, extreme, limit, expected
):
    q = replace(
        analysis(case_for("525142")).question,
        bound=relation,
        extreme=extreme,
        limit=sp.Rational(limit),
    )
    assert model.analyze(q).result == expected


@pytest.mark.parametrize(
    "mode",
    [
        "date",
        "header_unit",
        "first",
        "last",
        "increase",
        "expression",
        "row",
        "cell",
        "span",
        "instruction",
        "outside",
        "move",
    ],
)
def test_changed_or_ambiguous_table_is_never_guessed(mode):
    def edit(soup):
        rows = soup.table.select("tr")
        cells = rows[1].find_all(["td", "th"], recursive=False)
        if mode == "date":
            rows[0].select("td")[2].string = "Июль 2030"
        elif mode == "header_unit":
            cells[0].string = "Долг (в тыс. рублей)"
        elif mode == "first":
            cells[1].string = "0,9S"
        elif mode == "last":
            cells[-1].string = "0,1S"
        elif mode == "increase":
            cells[2].string = "1,1S"
        elif mode == "expression":
            cells[2].string = "0,8S+1"
        elif mode == "row":
            soup.table.tbody.append(rows[1].__copy__())
        elif mode == "cell":
            cells[2].decompose()
        elif mode == "span":
            cells[2]["colspan"] = "2"
        elif mode == "instruction":
            cells[2].append(" Выплаты до процентов.")
        elif mode == "outside":
            soup.table.append(" Не учитывать проценты.")
        else:
            soup.append(soup.table.extract())

    with pytest.raises(ValueError):
        edited("525142", edit)


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("525142", "20%", "0%"),
        ("525142", "5 млн", "0 млн"),
        ("513106", "15.04", "15.05"),
        ("513106", "100%", "99%"),
        ("701456", "2029 и 2030", "2029 и 2031"),
        ("701456", "2031", "2032"),
        ("701456", "70%", "100%"),
        ("701456", "70%", "0%"),
    ],
)
def test_inconsistent_dates_zero_amounts_and_invalid_reductions_are_rejected(
    task, old, new
):
    with pytest.raises(ValueError):
        changed(task, old, new)


def test_no_positive_integer_below_a_tiny_upper_bound_is_rejected():
    q = replace(analysis(case_for("525142")).question, limit=sp.Rational(1, 10))
    with pytest.raises(ValueError, match="positive integer"):
        model.analyze(q)


def test_corrupt_answers_have_independent_documented_corrections():
    overrides = {c["task"]: c for c in CASES if "expected_answer" in c}
    assert {task: c["expected_answer"] for task, c in overrides.items()} == {
        "549117": "320",
        "701459": "6000",
        "701515": "11000",
    }
    assert all(c["source_answer_note"] for c in overrides.values())
