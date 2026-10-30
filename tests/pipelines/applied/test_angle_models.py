"""Exact angular extrema, original poles and open versus closed endpoints."""

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

from solution_runner.pipelines.applied import angle_models as model
from solution_runner.pipelines.applied import angle_proof, angle_questions, common
from solution_runner.pipelines.applied.angle_questions import X

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_10_angles.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


def changed(task, old, new):
    text = angle_questions.normalize(common.read(sample(task)["context"])[3])
    assert old in text
    return model.analyze(angle_questions.parse(text.replace(old, new)))


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_all_groups_share_one_static_angle_rule(group):
    verify_registration(group)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_replays_compute_answers_without_mutation_or_saved_answer_dependency(
    case,
):
    verify_source(case)
    _, a = model.calculate(case["context"])
    assert a.question.domain.contains(a.angle) is sp.S.true
    assert a.result == a.angle * a.question.multiplier
    assert a.question.expression.subs(X, a.boundary) == a.question.target


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_unrecognized_instructions_and_foreign_assets_are_refused(case, leading):
    verify_rejection(case, leading)


def test_flight_can_be_vertical_while_explicitly_acute_angles_cannot_reach_ninety():
    _, vertical = model.calculate(sample("43153")["context"])
    assert vertical.angle == vertical.result == 90
    assert vertical.question.domain.right_open is sp.S.false
    with pytest.raises(ValueError, match="no physical"):
        changed("27999", "меньше 0,75", "меньше 1,5")
    with pytest.raises(ValueError, match="no physical"):
        changed("28008", "1600 нм", "800 нм")


def test_collision_returns_the_full_angle_and_allows_head_on_motion():
    _, a = model.calculate(sample("43741")["context"])
    assert a.angle == 45 and a.result == 90
    head_on = changed("28009", "менее 50", "менее 200")
    assert head_on.angle == 90 and head_on.result == 180
    with pytest.raises(ValueError, match="attained"):
        changed("28009", "менее 50", "менее 0")


def test_cosine_and_cotangent_are_inverted_in_the_decreasing_direction():
    _, cosine = model.calculate(sample("28011")["context"])
    _, emf = model.calculate(sample("28005")["context"])
    _, cotangent = model.calculate(sample("28010")["context"])
    assert cosine.result == emf.result == 60 and cotangent.result == 45
    assert cosine.question.maximum and not emf.question.maximum
    _, epsilon = model.calculate(sample("28601")["context"])
    assert epsilon.question.quantity == r"\epsilon_i"
    with pytest.raises(ValueError, match="attained"):
        changed("28011", "до 0,25", "до 0")
    with pytest.raises(ValueError, match="no physical"):
        changed("28010", "больше 200 с", "больше 0 с")
    with pytest.raises(ValueError, match="no physical"):
        changed("28005", r"10^{-4} В", "0 В")
    with pytest.raises(ValueError, match="attained"):
        changed("28005", r"10^{-4} В", r"2\cdot10^{-4} В")


def test_lorentz_uses_both_sine_branches_and_the_closed_interval():
    _, right_angle = model.calculate(sample("674966")["context"])
    assert right_angle.result == 90 and right_angle.question.domain == sp.Interval(
        0, 180
    )
    zero = changed("28002", r"2\cdot 10^{-8} Н", "0 Н")
    assert zero.result == 0
    html = solution(plan(sample("28002"), sample("28002")["context"]))
    assert "150" in html and "360n" in html and "возрастающую ветвь" in html


def test_diffraction_keeps_the_declared_angle_and_order():
    _, beta = model.calculate(sample("509418")["context"])
    _, third = model.calculate(sample("28639")["context"])
    assert beta.question.angle == r"\beta" and beta.result == 30
    assert third.question.values["order"] == 3 and third.result == 30
    with pytest.raises(ValueError, match="declared angle"):
        changed("509418", r"\sin \beta", r"\sin \alpha")


def test_bad_saved_boat_answer_is_recomputed_and_kilonewtons_match_kilojoules():
    case = sample("28657")
    saved = next(
        s["html"]
        for s in case["context"]["normalized_content"]["sections"]
        if s["key"] == "answer"
    )
    assert BeautifulSoup(saved, "html.parser").get_text() == "000"
    assert plan(case, case["context"]).answer == "45"
    _, tractor = model.calculate(sample("28006")["context"])
    assert tractor.question.expression == 4000 * X and tractor.question.target == 2000


def test_nonstandard_angles_and_original_denominator_holes_are_not_guessed():
    with pytest.raises(ValueError, match="rational degrees"):
        changed("28011", "до 0,25", "до 0,2")
    with pytest.raises(ValueError, match="vanishes"):
        changed(
            "28011",
            r"v\cos \alpha",
            r"v\cdot(\frac{1}{\frac{1}{\cos\alpha-\frac{1}{2}}}+\frac{1}{2})",
        )
    with pytest.raises(ValueError, match="physical angle law"):
        changed("28011", r"\frac{m}{m+M}", r"\frac{m}{m-M}")


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("28011", "m=80", "m=0"),
        ("28010", "u=0{,}5", "u=-1"),
        ("28006", "силой F=80", "силой F=0"),
        ("27999", "N=1000", "N=0"),
        ("28009", "менее 50", "менее -1"),
    ],
)
def test_negative_thresholds_and_nonpositive_physical_parameters_are_refused(
    task, old, new
):
    with pytest.raises(ValueError, match="positive"):
        changed(task, old, new)


@pytest.mark.parametrize(
    "case",
    [c for c in CASES if c["group"] in {"28003", "28004"}],
    ids=lambda c: c["task"],
)
def test_double_angle_intervals_agree_with_original_laws_on_both_branches(case):
    _, a = model.calculate(case["context"])
    q = a.question
    assert q.argument_multiplier == 2 and q.multiplier == 1
    assert q.domain == sp.Interval.open(0, 90)
    assert (
        q.expression.subs(
            X, {"sin": sp.sin, "cos": sp.cos}[q.function](2 * a.angle * sp.pi / 180)
        )
        == q.target
    )
    for angle in [0, 15, 30, 45, 60, 75, 90]:
        physical = q.domain.contains(angle)
        quantity = q.expression.subs(
            X, {"sin": sp.sin, "cos": sp.cos}[q.function](2 * angle * sp.pi / 180)
        )
        feasible = physical & sp.Ge(quantity, q.target)
        assert angle_proof.angular_interval(a).contains(angle) == feasible


def test_throw_height_uses_wall_plus_clearance_and_negative_cosines():
    a = changed("28003", "высотой 4 м", "высотой 14 м")
    assert a.question.target == 15 and a.angle == a.result == 60
    assert a.boundary == -sp.Rational(1, 2)
    assert model.value_domain(a.question) == sp.Interval.open(-1, 1)
    no_gap = changed(
        "28003", "высотой 4 м на расстоянии 1 м", "высотой 5 м на расстоянии 0 м"
    )
    assert no_gap.question.target == 5 and no_gap.result == 30


def test_maximum_range_is_attained_at_forty_five_but_zero_has_no_least_acute_angle():
    tangent = changed("28004", "шириной 20 м", "шириной 40 м")
    assert tangent.result == 45 and tangent.feasible_values == sp.FiniteSet(1)
    assert r"\left\{90\right\}" in angle_proof.proof(tangent)
    with pytest.raises(ValueError, match="no physical"):
        changed("28004", "шириной 20 м", "шириной 41 м")
    with pytest.raises(ValueError, match="attained"):
        changed("28004", "шириной 20 м", "шириной 0 м")
    with pytest.raises(ValueError, match="no physical"):
        changed("28003", "высотой 4 м", "высотой 19 м")


@pytest.mark.parametrize("task", ["28003", "28004"])
def test_argument_scale_is_checked_independently_of_output_scale(task):
    with pytest.raises(ValueError, match="argument scale"):
        changed(task, r"2\alpha", r"\alpha")
    with pytest.raises(ValueError):
        changed(task, r"2\alpha", r"3\alpha")
    with pytest.raises(ValueError, match="declared angle"):
        changed(task, r"2\alpha", r"2\beta")


def test_cancelled_pole_in_negative_cosine_half_of_double_angle_is_refused():
    with pytest.raises(ValueError, match="vanishes"):
        changed(
            "28003",
            r"\cos 2\alpha",
            r"(\frac{1}{\frac{1}{\cos 2\alpha+\frac{1}{2}}}-\frac{1}{2})",
        )


@pytest.mark.parametrize("task", ["28003", "28004"])
def test_double_angle_proof_preserves_argument_before_halving_bounds(task):
    case = sample(task)
    html = solution(plan(case, case["context"]))
    formulas = [
        tag["data-inline-latex"]
        for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert any(r"2\alpha\in" in formula for formula in formulas)
    if task == "28003":
        assert r"\cos 2\alpha\leq\frac{1}{2}" in formulas
        assert any("4+1=5" in formula for formula in formulas)
    else:
        assert any(r"2\alpha\in[30+360n;150+360n]" in formula for formula in formulas)
        assert r"\alpha\in\left[15, 75\right]\quad(\text{градусы})" in formulas
    assert "Делим границы промежутка на 2" in html


@pytest.mark.parametrize("task", ["28007", "28623"])
def test_malformed_power_units_are_repaired_locally_without_changing_the_law(task):
    from solution_runner.pipelines.applied.power_units import UNIT

    case = sample(task)
    original = next(
        s["html"]
        for s in case["context"]["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    prepared = plan(case, case["context"])
    repaired = prepared.condition_html
    assert original != repaired and UNIT in repaired
    formulas = lambda html: [
        tag["data-inline-latex"]
        for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert formulas(original)[:-1] == formulas(repaired)[:-1]
    assert prepared.answer == "60"
    assert model.calculate(case["context"])[1].question.values["repair_unit"]
    if task == "28623":
        answer = next(
            s["html"]
            for s in case["context"]["normalized_content"]["sections"]
            if s["key"] == "answer"
        )
        assert BeautifulSoup(answer, "html.parser").get_text() == "000"


@pytest.mark.parametrize(
    "old,new,error",
    [
        ("равна 75 кВт", "равна 0 кВт", "no physical"),
        ("равна 75 кВт", "равна 150 кВт", "no physical"),
        ("силой F=50", "силой F=0", "positive"),
        (r"\mathrm{C}", r"\mathrm{час}", "power unit"),
        (r"F v\cos", r"F v^2\cos", "physical angle law"),
    ],
)
def test_power_law_units_and_acute_endpoints_are_checked(old, new, error):
    with pytest.raises(ValueError, match=error):
        changed("28007", old, new)
