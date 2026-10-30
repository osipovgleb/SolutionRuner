"""Exact fractional gas powers, inverse changes and pressure feasibility."""

import json
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

from solution_runner.pipelines.applied import common, gas_questions
from solution_runner.pipelines.applied import gas_models as model

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_10_gases.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


def changed(task, old, new):
    text = common.read(sample(task)["context"])[3]
    assert old in text
    return model.analyze(gas_questions.parse(text.replace(old, new)))


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_gas_groups_share_one_positive_power_rule(group):
    verify_registration(group)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_answers_are_exact_and_independent_of_saved_answers(case):
    verify_source(case)
    _, a = model.calculate(case["context"])
    v = a.question.values
    assert a.result.is_Rational and a.result > 0
    if a.question.kind == "factor":
        assert v["volume_factor"] ** a.result == v["pressure_factor"]
    elif a.question.kind == "absolute":
        assert (
            sp.simplify(v["pressure"] * a.result ** v["exponent"] - v["constant"]) == 0
        )
    else:
        assert (
            sp.simplify(
                v["pressure"] * a.result ** v["exponent"]
                - v["initial"] ** v["exponent"]
            )
            == 0
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_extra_instructions_or_assets_are_not_ignored(case, leading):
    verify_rejection(case, leading)


def test_pressure_limit_and_exact_compression_are_distinct_requests():
    _, minimum = model.calculate(sample("27993")["context"])
    _, equal = model.calculate(sample("504257")["context"])
    assert (
        minimum.question.kind == "compression_min"
        and equal.question.kind == "compression_equal"
    )
    assert minimum.ratio == equal.ratio == 32
    assert changed("27993", "128 атмосфер", "1 атмосфер").result == sp.Rational(8, 5)
    with pytest.raises(ValueError, match="compression"):
        changed("27993", "128 атмосфер", "0,5 атмосфер")


def test_volume_increase_and_decrease_use_opposite_pressure_ratios():
    _, compression = model.calculate(sample("27992")["context"])
    _, expansion = model.calculate(sample("28441")["context"])
    assert compression.question.values["compression"] is True
    assert expansion.question.values["compression"] is False
    assert expansion.result == sp.Rational(1, 2)
    with pytest.raises(ValueError, match="opposite"):
        changed("27992", "к увеличению", "к уменьшению")
    with pytest.raises(ValueError, match="greater than one"):
        changed("27992", "в два раза", "в 1 раза")


def test_fractional_powers_are_not_rounded_and_dimensions_are_checked():
    with pytest.raises(ValueError, match="rational"):
        changed("27992", "в 4 раза?", "в 3 раза?")
    with pytest.raises(ValueError, match="rational"):
        changed("27993", "128 атмосфер", "129 атмосфер")
    with pytest.raises(ValueError, match="units"):
        changed("27990", r"м^{5}", r"м^{4}")
    with pytest.raises(ValueError, match="same exponent"):
        changed("525114", r"p_2V_2^{1{,}4}", r"p_2V_2^{1{,}5}")


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("27993", "равен 1,6 л", "равен 0 л"),
        ("27990", r"k=\frac{5}{3}", "k=0"),
        ("27990", r"3{,}2\cdot 10^{6} Па.", "-1 Па."),
        ("27992", "в 4 раза?", "в 0 раза?"),
    ],
)
def test_nonpositive_gas_data_are_refused(task, old, new):
    with pytest.raises(ValueError, match="positive"):
        changed(task, old, new)
