"""Shared oscillation energy, signed velocities and exact irrational intermediates."""

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

from solution_runner.pipelines.applied import common
from solution_runner.pipelines.applied import harmonic_models as model

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_10_harmonics.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


def changed(old, new, task="28012"):
    text = common.read(sample(task)["context"])[3]
    assert old in text
    return model.analyze(model.parse(text.replace(old, new)))


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_sine_and_cosine_share_one_energy_rule(group):
    verify_registration(group)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_replays_compute_exact_answers_and_are_idempotent(case):
    verify_source(case)
    _, a = model.calculate(case["context"])
    assert a.result == a.question.mass * a.velocity**2 / 2
    assert a.result >= 0


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_unread_instructions_and_foreign_assets_are_refused(case, leading):
    verify_rejection(case, leading)


@pytest.mark.parametrize("task", ["513877", "513878", "28013", "513932"])
def test_negative_velocity_is_kept_until_the_energy_is_squared(task):
    case = sample(task)
    _, a = model.calculate(case["context"])
    assert a.velocity < 0 < a.result
    formulas = [
        tag["data-inline-latex"]
        for tag in BeautifulSoup(
            solution(plan(case, case["context"])), "html.parser"
        ).select("[data-inline-latex]")
    ]
    assert any(
        sp.latex(a.velocity) in formula and "^2" in formula for formula in formulas
    )


def test_full_periods_zero_velocity_and_surd_velocity_are_exact():
    zero = changed("через 1 секунду", "через 0 секунд")
    assert zero.phase == zero.velocity == zero.result == 0
    periods = changed("через 1 секунду", "через 120000 секунд")
    assert periods.velocity == periods.result == 0
    surd = changed("T=12 с", "T=8 с")
    assert surd.velocity == sp.sqrt(2) / 4 and surd.result == sp.Rational(1, 200)
    cosine = changed("через 1 секунду", "через 0 секунд", "28013")
    assert cosine.velocity == sp.Rational(1, 2) and cosine.result == sp.Rational(1, 100)
    with pytest.raises(ValueError, match="without rounding"):
        changed("T=12 с", "T=7 с")


@pytest.mark.parametrize(
    "old,new,error",
    [
        ("массой 0,08", "массой 0", "positive"),
        ("T=12", "T=0", "positive"),
        ("v_0=0{,}5", "v_0=-0{,}5", "positive"),
        ("через 1 секунду", "через -1 секунду", "nonnegative"),
        (r"2\pi t", r"\pi t", "laws"),
        (r"\frac{m v^{2}}{2}", r"\frac{m v^{2}}{3}", "laws"),
        (r"\frac{2\pi t}{T}", r"\frac{2\pi t}{T}+1", "laws"),
        ("м/с", "км/ч", "recognized"),
        ("в джоулях.", "в килоджоулях.", "recognized"),
    ],
)
def test_nonphysical_data_changed_laws_and_units_fail_closed(old, new, error):
    with pytest.raises(ValueError, match=error):
        changed(old, new)
