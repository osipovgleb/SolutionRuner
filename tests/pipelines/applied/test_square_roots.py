"""Square-root source replays, exact conversions and discrete minimum checks."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
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

from solution_runner.pipelines.applied import (
    common,
    fraction_questions,
    horizon_assets,
    root_proof,
)
from solution_runner.pipelines.applied import rational_models as model
from solution_runner.pipelines.applied.fraction_questions import X
from solution_runner.pipelines.applied.rational_formula import SquareRootFormulaParser

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_10_roots.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


def changed(task, old, new):
    text = common.read(sample(task)["context"])[3]
    assert old in text
    return model.analyze(fraction_questions.parse(text.replace(old, new)))


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_root_groups_reuse_the_physical_constraint_rule(group):
    verify_registration(group)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_replays_compute_exact_answers_without_mutation(case):
    verify_source(case)
    _, a = model.calculate(case["context"])
    assert a.feasible.contains(a.result) is sp.S.true
    if a.question.kind == "root_steps":
        assert a.result.is_Integer
        assert a.question.expression.subs(X, a.result) >= a.question.target
    else:
        assert a.question.expression.subs(X, a.result) == a.question.target


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_extra_instructions_and_assets_fail_closed(case, leading):
    verify_rejection(case, leading)


def test_acceleration_equation_threshold_and_metres_remain_distinct():
    _, equal = model.calculate(sample("27982")["context"])
    _, threshold = model.calculate(sample("510982")["context"])
    assert equal.question.relation == "eq" and threshold.question.relation == "ge"
    assert equal.result == threshold.result == 5000
    _, metres = model.calculate(sample("510825")["context"])
    assert metres.question.values["native_path"] == sp.Rational(1, 4)
    assert metres.result == 7200
    assert changed("510825", "250 метров", "500 метров").result == 3600
    with pytest.raises(ValueError, match="no physical"):
        changed("27982", "скорость 100", "скорость 0")
    with pytest.raises(ValueError, match="attained"):
        changed("510982", "менее 100", "менее 0")


def test_distance_uses_native_acceleration_units_before_answer_conversion():
    _, metres = model.calculate(sample("523372")["context"])
    _, kilometres = model.calculate(sample("523397")["context"])
    assert metres.result == 1125 and metres.question.unit == "м"
    assert kilometres.result == sp.Rational(7, 8) and kilometres.question.unit == "км"
    html = solution(plan(sample("523397"), sample("523397")["context"]))
    assert "875" in html and r"\frac{1}{1000}" in html
    zero = changed("523397", "35 м/с", "0 м/с")
    assert zero.result == 0
    assert r"\frac{1}{1000}" in root_proof.motion(zero)
    with pytest.raises(ValueError, match="consistent"):
        changed("523397", "35 м/с", "35 км/ч")
    with pytest.raises(ValueError, match="declared path"):
        changed(
            "523397",
            "пройденный автомобилем путь.",
            "пройденный автомобилем путь в км.",
        )


def test_horizon_metres_and_kilometres_differ_by_exactly_one_thousand():
    _, metres = model.calculate(sample("27984")["context"])
    _, kilometres = model.calculate(sample("263802")["context"])
    assert metres.result == 1000 * kilometres.result == sp.Rational(5, 4)
    assert changed("27984", "R=6400", "R=8000").result == 1
    for task in ["27984", "263802"]:
        assert "Примечание" in solution(plan(sample(task), sample(task)["context"]))
    with pytest.raises(ValueError, match="physical law"):
        changed("27984", r"\frac{Rh}{500}", r"\frac{Rh}{1000}")


def test_steps_use_the_least_whole_number_including_exact_and_zero_cases():
    a = changed("27986", "высоту 20 см", "высоту 30 см")
    assert a.result == 5
    assert a.question.expression.subs(X, 4) < a.question.target
    assert a.question.expression.subs(X, 5) >= a.question.target
    assert changed("27986", "высоту 20 см", "высоту 14 см").result == 10
    assert changed("27986", "менее 6,4", "менее 4,8").result == 0
    assert changed("27986", "менее 6,4", "менее 3,2").result == 0


def test_rocket_uses_a_strict_subluminal_domain_and_refuses_zero_length():
    _, a = model.calculate(sample("27983")["context"])
    assert a.result == 180000 and a.question.domain == sp.Interval.Ropen(0, 300000)
    assert changed("27983", "более 4 м", "более 5 м").result == 0
    assert changed("27983", "более 4 м", "более 6 м").result == 0
    with pytest.raises(ValueError, match="no physical"):
        changed("27983", "более 4 м", "более 0 м")
    with pytest.raises(ValueError, match="rational"):
        changed("27983", "более 4 м", "более 1 м")


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("27982", "скорость 100", "скорость -100"),
        ("27984", "R=6400", "R=0"),
        ("27986", "высоту 20 см", "высоту 0 см"),
        ("27983", "l _0=5", "l _0=0"),
        ("523397", "a=0,7", "a=0"),
    ],
)
def test_signs_and_positive_physical_parameters_are_checked_before_squaring(
    task, old, new
):
    with pytest.raises(ValueError, match="physical"):
        changed(task, old, new)


def test_root_grammar_keeps_original_denominators_and_rejects_extra_radicals():
    formula = r"\sqrt{\frac{Rh}{500}}"
    with pytest.raises(ValueError, match="vanishes"):
        changed("27984", formula, r"\sqrt{\frac{Rh}{500}\cdot\frac{h}{h}}")
    with pytest.raises(ValueError, match="square-root formula"):
        changed("27984", formula, r"\sqrt{1}\cdot" + formula)
    parser = SquareRootFormulaParser(r"\sqrt{\frac{x}{x}}", "x")
    assert parser.parse() == 1 and parser.denominators == [X]
    with pytest.raises(ValueError):
        SquareRootFormulaParser(r"\sqrt{x", "x").parse()


def test_horizon_ascent_keeps_the_independent_conductor_example_for_every_child():
    for task, expected in [
        ("27985", sp.Rational(7, 5)),
        ("28365", 6),
        ("42635", sp.Rational(715, 4)),
        ("525065", sp.Rational(24, 5)),
    ]:
        case = sample(task)
        result = plan(case, case["context"])
        assert sp.Rational(result.answer.replace(",", ".")) == expected
        html = solution(result)
        assert horizon_assets.ASSET_ID in html and "Примечание Дмитрия Гущина" in html
        assert "не относятся к задаче о горизонте" in html
        changes = [
            t
            for t in result.transformations
            if t["transformation_target_id"].startswith("section:solution")
        ]
        assert len(changes[0]["value"]["asset_keys"]) == 1
        assert not any(
            t["transformation_target_id"].startswith("asset:")
            for t in result.transformations
        )


def test_horizon_example_rejects_foreign_asset_identity_url_or_placement():
    for mode in ["identity", "url", "placement"]:
        context = deepcopy(sample("27985")["context"])
        content = context["normalized_content"]
        if mode == "identity":
            content["assets"][0]["asset_id"] = "foreign"
        elif mode == "url":
            content["assets"][0]["url"] = "https://example.org/foreign.png"
        else:
            next(s for s in content["sections"] if s["key"] == "condition")[
                "asset_keys"
            ] = ["image_1"]
        with pytest.raises(ValueError):
            plan(sample("27985"), context)
    with pytest.raises(ValueError, match="increase"):
        changed("28365", "до 10,4", "до 5,6")
