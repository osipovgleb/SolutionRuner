"""Conserved components, physical domains and complete source solution replay."""

import json
from pathlib import Path

import pytest
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
from solution_runner.pipelines.word_problems import mixture_models as model
from solution_runner.pipelines.word_problems.mixture_questions import parse

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_11_mixtures.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


def changed(task, *replacements):
    text = math_common.read(sample(task)["context"])[3]
    for old, new in replacements:
        assert old in text
        text = text.replace(old, new)
    return model.analyze(parse(text))


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_ten_groups_share_one_conservation_rule(group):
    verify_registration(group)
    assert group["rule"] == "word-mixture-balance"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_source_answers_are_independent_and_prepared_changes_are_idempotent(case):
    verify_source(case)
    result = plan(case)
    condition = next(
        s["html"]
        for s in case["context"]["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    assert result.condition_html == condition


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_unread_instructions_and_unknown_figures_are_refused(case, mode):
    verify_rejection(case, mode)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_original_component_balances_hold_for_every_source(case):
    _, a = model.calculate(case["context"])
    q, v = a.question, a.question.values
    m1, m2 = a.amounts
    c1, c2 = a.fractions
    assert m1 > 0 and m2 >= 0 and 0 <= c1 <= 1 and 0 <= c2 <= 1
    if q.kind in ["dilution", "equal", "weighted"]:
        assert a.result == 100 * (m1 * c1 + m2 * c2) / (m1 + m2)
        assert min(v["p1"], v["p2"]) <= a.result <= max(v["p1"], v["p2"])
    elif q.kind == "drying":
        assert m1 * c1 == m2 * c2 and m1 > m2 and a.result == m1
    elif q.kind in ["alloy_total", "alloy_difference"]:
        assert m1 * c1 + m2 * c2 == (m1 + m2) * v["target"] / 100
        if q.kind == "alloy_total":
            assert m1 + m2 == v["total"] and a.result == m2 - m1 > 0
        else:
            assert m2 - m1 == v["difference"] and a.result == m1 + m2
    elif q.kind == "two_scenarios":
        pure = m1 * c1 + m2 * c2
        assert 100 * pure / (m1 + m2 + v["water"]) == v["target"]
        assert (
            100 * (pure + v["added"] * v["alternative"] / 100) / (m1 + m2 + v["added"])
            == v["second_target"]
        )
        assert a.result == m1
    elif q.kind == "unknown_concentrations":
        assert (c1 + c2) / 2 == v["mean"] / 100
        assert (m1 * c1 + m2 * c2) / (m1 + m2) == v["target"] / 100
        assert c1 != c2 and a.result == m1 * c1
    elif q.kind == "ratio":
        assert c1 / c2 == v["r1"] / v["r2"]
        assert (c1 + c2) / 2 == v["target"] / 100
        assert a.result == 100 * (c2 - c1)
    else:
        assert q.kind == "acid_difference"
        assert c1 - c2 == v["difference"] / 100
        assert m1 * c1 == v["acid1"] and m2 * c2 == v["acid2"]
        assert m1 + m2 == v["total"] and a.result == 100 * c1


def test_mass_and_volume_use_their_own_symbols_and_keep_the_parent_note():
    volume = plan(sample("99571")).solution_html
    mass = plan(sample("108651")).solution_html
    assert r"V_{\mathrm{в-ва}}" in volume
    assert r"m_{\mathrm{в-ва}}" in mass
    assert "В действительности объем" in volume and "В действительности объем" in mass
    assert "заданы массы" in mass
    assert "Конечно, вместо литров" in plan(sample("99573")).condition_html.replace(
        "\u00ad", ""
    )


def test_the_counterfactual_can_replace_water_with_a_different_amount_of_solution():
    a = changed(
        "99577", ("добавили 10 кг 50", "добавили 20 кг 50"), ("41-", r"\frac{460}{11}-")
    )
    assert a.amounts == (60, 30) and a.result == 60


def test_ratio_difference_is_signed_and_reverses_when_the_order_reverses():
    a = changed("676853", ("2: 5", "5: 2"))
    assert a.result == -42


def test_dilution_allows_zero_added_water_and_zero_initial_solute():
    assert changed("99571", ("добавили 7 литров", "добавили 0 литров")).result == 12
    assert changed("99571", ("12-", "0-")).result == 0


@pytest.mark.parametrize(
    "task,replacements,error",
    [
        ("99571", [("добавили 7 литров", "добавили -1 литров")], "amounts"),
        ("99571", [("5 литров", "0 литров")], "positive"),
        ("99571", [("12-", "101-")], "concentrations"),
        ("99571", [("7 литров", "7 кг")], "same physical unit"),
        ("99574", [("90%", "100%")], "drying"),
        ("99574", [("5%", "95%")], "drying"),
        ("99574", [("20 килограммов", "0 килограммов")], "positive"),
        ("99575", [("30%", "10%")], "unique"),
        ("99575", [("25%", "35%")], "positive"),
        ("99575", [("25%", "15%")], "positive"),
        ("99576", [("30%", "25%")], "unique"),
        ("99576", [("на 3 кг", "на 0 кг")], "positive"),
        ("99577", [("вместо 10 кг", "вместо 11 кг")], "counterfactual"),
        ("99577", [("килограммов 30-", "килограммов 60-")], "requested"),
        ("99578", [("30 кг", "20 кг")], "unique"),
        ("99578", [("70%", "99%")], "physical concentrations"),
        ("99578", [("70%", "68%")], "distinct"),
        ("639947", [("на 20 больше", "на 0 больше")], "difference"),
        ("639947", [("400 г", "100 г")], "acid masses"),
        ("639947", [("400 г", "401 г")], "exact rational"),
        ("676853", [("49%", "99%")], "cannot exceed"),
        ("676853", [("2: 5", "0: 5")], "positive"),
    ],
)
def test_underdetermined_impossible_and_nonrational_questions_fail_closed(
    task, replacements, error
):
    with pytest.raises(ValueError, match=error):
        changed(task, *replacements)
