"""Rational physical source replays, bounded ranges and uncancelled pole checks."""

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
from solution_runner.pipelines.applied import rational_models as model
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
    for text in [
        r"\frac{x}{x",
        r"\sqrt{2}",
        "__import__('os')",
        "x^7",
        "x(1+x)",
        "x^0",
        "x^{-1}",
        "|x",
    ]:
        with pytest.raises(ValueError):
            RationalFormulaParser(text, "x").parse()
    parser = RationalFormulaParser(r"\frac{x}{\frac{1}{x-1}}", "x")
    assert parser.parse() == X * (X - 1)
    assert X - 1 in parser.denominators and 1 / (X - 1) in parser.denominators


def test_lens_intersects_both_ranges_instead_of_always_using_the_screen_maximum():
    a = changed("27970", "от 30 до 50", "от 37 до 50")
    assert a.result == 37
    assert a.question.expression.subs(X, a.result) == sp.Rational(1110, 7)
    assert a.feasible == sp.Interval(37, sp.Rational(75, 2))
    one = changed("27970", "от 30 до 50", "от 36 до 36")
    assert one.result == 36 and one.feasible == sp.FiniteSet(36)
    screen_point = changed("27970", "от 150 до 180", "от 180 до 180")
    assert screen_point.result == 36 and screen_point.feasible == sp.FiniteSet(36)


@pytest.mark.parametrize(
    "old,new",
    [
        ("от 30 до 50", "от 30 до 35"),
        ("от 30 до 50", "от 10 до 20"),
        ("от 150 до 180", "от 10 до 20"),
        ("от 30 до 50", "от 50 до 30"),
        ("f=30", "f=0"),
    ],
)
def test_lens_empty_reversed_or_nonpositive_ranges_are_refused(old, new):
    with pytest.raises(ValueError):
        changed("27970", old, new)


def test_lens_does_not_cancel_unchecked_distance_poles():
    left = r"\frac{1}{d_1}+\frac{1}{d_2}"
    with pytest.raises(ValueError, match="vanishes"):
        changed("27970", left, "(" + left + r")\cdot\frac{d_1-40}{d_1-40}")
    with pytest.raises(ValueError, match="screen denominator"):
        changed("27970", left, "(" + left + r")\cdot\frac{d_2-160}{d_2-160}")
    with pytest.raises(ValueError, match="contradicts"):
        changed("27970", r"\frac{1}{f}", r"\frac{2}{f}")


def test_enlargement_is_enforced_and_only_an_impossible_qualifier_is_repaired():
    text = common.read(sample("27970")["context"])[3]
    wide = text.replace("от 30 до 50", "от 30 до 100").replace(
        "от 150 до 180", "от 40 до 180"
    )
    a = model.analyze(fraction_questions.parse(wide))
    assert a.feasible == sp.Interval.Ropen(36, 60) and not a.repair_lens_wording
    case = sample("41895")
    _, reduced = model.calculate(case["context"])
    assert reduced.result == 336 and reduced.repair_lens_wording
    assert reduced.question.expression.subs(X, reduced.result) == 105 < reduced.result
    result = plan(case, case["context"])
    repair = next(
        t
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:condition")
    )
    corrected = repair["value"]["html"]
    assert "действительного" in BeautifulSoup(
        corrected, "html.parser"
    ).get_text().replace("\u00ad", "")
    original = next(
        s["html"]
        for s in case["context"]["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    formulas = lambda html: [
        s["data-inline-latex"]
        for s in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert formulas(corrected) == formulas(original)


def test_resonance_cancels_amplitude_only_on_the_below_resonance_branch():
    _, a = model.calculate(sample("27974")["context"])
    assert a.question.target == sp.Rational(9, 8)
    assert a.feasible == sp.Interval(0, 120)
    assert a.question.expression.subs(X, 0) == 1
    assert a.question.domain.contains(360) is sp.S.false
    assert changed("27974", r"12{,}5\%", r"0\%").result == 0
    html = solution(plan(sample("27974"), sample("27974")["context"]))
    assert "Примечание" in html and r"\frac{25}{2}\%" in html
    with pytest.raises(ValueError, match="rational"):
        changed("27974", r"12{,}5\%", r"100\%")
    with pytest.raises(ValueError, match="recognized"):
        changed("27974", "меньшую резонансной", "большую резонансной")
    with pytest.raises(ValueError, match="positive resonance"):
        changed("27974", r"\omega_p=360", r"\omega_p=0")


def test_squared_and_absolute_formula_operands_keep_original_poles():
    parser = RationalFormulaParser(r"\frac{x^2-1}{|x^2-1|}", "x")
    assert parser.parse() == (X**2 - 1) / sp.Abs(X**2 - 1)
    assert parser.denominators == [sp.Abs(X**2 - 1)]
    formula = r"\frac{A_0\omega_p^{2}}{\left|\omega_p^{2}-\omega^{2}\right|}"
    with pytest.raises(ValueError, match="vanishes"):
        changed("27974", formula, formula + r"\cdot\frac{\omega-100}{\omega-100}")
    with pytest.raises(ValueError, match="contradicts"):
        changed("27974", formula, formula.replace("-", "+"))
