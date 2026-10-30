"""Linear-fraction source replays, unattained limits and uncancelled pole checks."""

import json
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_algebraic_formulas import (
    test_shared_scalar_rule_registration as verify_registration,
)
from test_algebraic_formulas import (
    test_source_answers_are_computed_without_mutation_and_idempotently as verify_source,
)
from test_algebraic_formulas import (
    test_unread_instructions_and_foreign_assets_cannot_be_ignored as verify_rejection,
)
from test_physical_polynomials import plan, solution

from solution_runner.pipelines.applied import common, fraction_questions
from solution_runner.pipelines.applied import linear_fractions as model
from solution_runner.pipelines.applied.fraction_questions import X
from solution_runner.pipelines.applied.rational_formula import RationalFormulaParser

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_10_fractions.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


def changed(task, old, new):
    text = common.read(sample(task)["context"])[3]
    assert old in text
    return model.analyze(fraction_questions.parse(text.replace(old, new)))


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_one_shared_rule_matches_catalogue_metadata(group):
    verify_registration(group)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_exact_source_replays_are_independent_of_saved_answers(case):
    verify_source(case)
    _, a = model.calculate(case["context"])
    assert a.question.domain.contains(a.result) is sp.S.true
    assert a.question.expression.subs(X, a.result) == a.question.target


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_extra_instructions_and_assets_are_refused(case, leading):
    verify_rejection(case, leading)


def test_fraction_of_short_circuit_current_allows_zero_external_resistance():
    assert changed("27972", "20\\%", "100\\%").result == 0
    assert changed("27972", "20\\%", "120\\%").result == 0
    with pytest.raises(ValueError, match="no physical"):
        changed("27972", "20\\%", "0\\%")


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("27975", "не меньше 9", "не меньше 90"),
        ("27979", "не менее 50", "не менее 55"),
        ("27976", "меньше 15", "меньше 100"),
        ("27981", "равна 2", "равна 1500"),
    ],
)
def test_asymptotic_limits_are_not_finite_solutions(task, old, new):
    with pytest.raises(ValueError, match="no physical"):
        changed(task, old, new)


def test_open_zero_and_unbounded_speed_have_no_attained_extremum():
    with pytest.raises(ValueError, match="attained"):
        changed("27975", "не меньше 9", "не меньше 0")
    with pytest.raises(ValueError, match="attained"):
        changed("27980", "менее 160", "менее 150")
    assert changed("27979", "не менее 50", "не менее 0").result == 0
    assert changed("27976", "меньше 15", "меньше 0").result == 340
    assert changed("27981", "равна 2", "равна 0").result == 749
    assert changed("27971", "чем на 10", "чем на 0").result == 0


def test_medium_equality_and_greek_source_speed_remain_an_equation():
    _, a = model.calculate(sample("516252")["context"])
    assert a.question.relation == "eq" and a.feasible == sp.FiniteSet(400)
    html = solution(plan(sample("516252"), sample("516252")["context"]))
    assert r"\geq" not in html and r"\max" not in html
    formulas = [
        s["data-inline-latex"]
        for s in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert any("c" in f and "400" in f for f in formulas)


def test_train_uses_frequency_difference_and_preserves_the_subsonic_pole():
    _, a = model.calculate(sample("27971")["context"])
    assert a.question.target == 450 and a.feasible == sp.Interval.Ropen(7, 315)
    assert a.question.expression.subs(X, 7) - 440 == 10
    _, b = model.calculate(sample("27980")["context"])
    assert b.feasible == sp.Interval.Lopen(15, 390)


@pytest.mark.parametrize("task,label", [("27975", "R_2"), ("27976", "T_1")])
def test_indexed_extrema_have_grouped_labels_without_a_double_subscript(task, label):
    html = solution(plan(sample(task), sample(task)["context"]))
    assert label + r"_{\min}" not in html
    assert "{" + label + r"}_{\min}" in html


def test_original_poles_cannot_disappear_by_cancellation():
    formula = r"\frac{T_1-T_2}{T_1}\cdot 100"
    with pytest.raises(ValueError, match="vanishes"):
        changed("27976", formula, formula + r"\cdot\frac{T_1-T_2}{T_1-T_2}")
    with pytest.raises(ValueError, match="denominator is zero"):
        changed("27976", formula, formula + r"\cdot\frac{T_2-T_2}{T_2-T_2}")
    with pytest.raises(ValueError, match="undeclared"):
        changed("27976", formula, formula + r"\cdot\frac{a}{a}")


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("27971", "c=315", "c=0"),
        ("27972", "r=1", "r=-1"),
        ("27976", "T_2=340", "T_2=0"),
        ("27979", r"\epsilon=55", r"\epsilon=-55"),
        ("27981", "частотой 749", "частотой 0"),
    ],
)
def test_impossible_physical_parameters_are_refused(task, old, new):
    with pytest.raises(ValueError, match="physical"):
        changed(task, old, new)


def test_unknown_units_changed_laws_and_malformed_formulas_fail_closed():
    with pytest.raises(ValueError, match="recognized"):
        changed("27979", "в омах.", "в килоомах.")
    with pytest.raises(ValueError, match="contradicts"):
        changed("27972", r"\frac{\epsilon}{r}", r"\frac{\epsilon}{R}")
    for text in [r"\frac{x}{x", r"\sqrt{2}", "__import__('os')", "x^2", "x(1+x)"]:
        with pytest.raises(ValueError):
            RationalFormulaParser(text, "x").parse()
    parser = RationalFormulaParser(r"\frac{x}{\frac{1}{x-1}}", "x")
    assert parser.parse() == X * (X - 1)
    assert X - 1 in parser.denominators and 1 / (X - 1) in parser.denominators
