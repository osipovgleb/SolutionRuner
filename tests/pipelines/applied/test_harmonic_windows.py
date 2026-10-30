"""Periodic time shares, physical units, exact clipping and rounded output."""

import json
import math
from dataclasses import replace
from fractions import Fraction
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

from solution_runner.pipelines.applied import common, window_questions
from solution_runner.pipelines.applied import harmonic_windows as model

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_10_windows.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


def changed(task, old, new):
    text = common.read(sample(task)["context"])[3]
    assert old in text
    return model.analyze(window_questions.parse(text.replace(old, new)))


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_both_groups_share_one_periodic_window_rule(group):
    verify_registration(group)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_replay_computes_answers_without_mutation_or_answer_dependency(case):
    verify_source(case)
    _, a = model.calculate(case["context"])
    assert a.duration == a.times.measure
    assert 0 <= a.fraction <= 1


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_unread_instructions_and_foreign_assets_are_refused(case, leading):
    verify_rejection(case, leading)


def test_three_second_window_divides_duration_by_three():
    _, a = model.calculate(sample("28709")["context"])
    assert a.times == sp.Interval.Lopen(sp.Rational(5, 6), 3)
    assert a.duration == sp.Rational(13, 6) and a.fraction == sp.Rational(13, 18)
    assert model.rendered_answer(a) == "0,72"
    html = solution(plan(sample("28709"), sample("28709")["context"]))
    formulas = [
        tag["data-inline-latex"]
        for tag in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    assert r"\frac{\Delta t}{3}=\frac{13}{18}" in formulas
    assert any(r"2 \pi n" in formula for formula in formulas)


def test_sensor_cosine_phase_and_partial_window_are_not_treated_as_sine():
    _, cosine = model.calculate(sample("28001")["context"])
    _, full = model.calculate(sample("28541")["context"])
    _, clipped = model.calculate(sample("525723")["context"])
    assert cosine.question.function == "cos" and cosine.question.phase == -120
    assert cosine.times == sp.Interval(sp.Rational(1, 4), sp.Rational(3, 4))
    assert full.result == 100 and clipped.result == 70


@pytest.mark.parametrize("function", ["sin", "cos"])
@pytest.mark.parametrize("frequency", [120, 360, 720])
@pytest.mark.parametrize("phase", [-450, 0, 30])
@pytest.mark.parametrize("level", [-3, -2, -1, 0, 1, 2, 3])
def test_exact_measure_matches_independent_cells_with_aligned_transition_boundaries(
    function, frequency, phase, level
):
    _, source = model.calculate(sample("28000")["context"])
    q = replace(
        source.question,
        function=function,
        frequency=sp.Integer(frequency),
        phase=sp.Integer(phase),
        level=sp.Integer(level),
    )
    a = model.analyze(q)
    # For these table levels and phases every transition lies on the 1/120 grid.
    trig = {"sin": math.sin, "cos": math.cos}[function]
    active = sum(
        2 * trig(math.radians(frequency * (i + 0.5) / 120 + phase)) >= level
        for i in range(120)
    )
    assert Fraction(a.fraction) == Fraction(active, 120)


def test_strict_threshold_keeps_open_boundaries_but_not_a_different_duration():
    _, source = model.calculate(sample("28014")["context"])
    strict = model.analyze(replace(source.question, strict=True))
    assert source.times.contains(sp.Rational(1, 6)) is sp.S.true
    assert strict.times.contains(sp.Rational(1, 6)) is sp.S.false
    assert source.duration == strict.duration
    peak = model.analyze(replace(source.question, level=sp.Integer(5)))
    strict_peak = model.analyze(
        replace(source.question, level=sp.Integer(5), strict=True)
    )
    assert peak.times == sp.FiniteSet(sp.Rational(1, 2))
    assert strict_peak.times is sp.S.EmptySet
    assert peak.duration == strict_peak.duration == 0
    low = model.analyze(
        replace(
            source.question, level=sp.Integer(-5), strict=True, window=sp.Integer(2)
        )
    )
    assert low.duration == 2 and low.times.contains(sp.Rational(3, 2)) is sp.S.false


def test_multiple_periods_and_half_up_rounding_use_exact_lengths():
    _, source = model.calculate(sample("28014")["context"])
    a = model.analyze(
        replace(
            source.question,
            amplitude=sp.Integer(2),
            level=sp.Integer(1),
            frequency=sp.Integer(60),
            window=sp.Integer(16),
        )
    )
    assert isinstance(a.times, sp.Union) and len(a.times.args) == 3
    assert a.duration == 6 and a.fraction == sp.Rational(3, 8)
    assert model.rendered_answer(a) == "0,38"
    with pytest.raises(ValueError, match="too many periodic"):
        model.analyze(replace(a.question, frequency=sp.Integer(360000)))


@pytest.mark.parametrize(
    "task,old,new,error",
    [
        ("28000", "U_0=2 В", "U_0=0 В", "positive"),
        ("28000", "ω=120", "ω=-120", "positive"),
        ("28000", "120°/с", "120 рад/с", "recognized"),
        ("28000", r"\omega t+\varphi", r"\omega t-\varphi", "sensor law"),
        ("28000", r"U_0\sin", r"2U_0\sin", "sensor law"),
        ("28014", r"\pi t", r"\pi t^2", "linear rational-pi"),
        ("28014", r"\pi t", r"\frac{\pi t^2}{t}", "variable denominators"),
        ("28014", r"5\sin", r"-5\sin", "positive"),
        ("28014", "из первой секунды", "из первых ноль секунд", "positive"),
        ("28014", "не менее 2,5", "не менее 2", "rational-degree"),
        ("28014", "см/с", "м/с", "recognized"),
    ],
)
def test_changed_units_nonlinear_laws_holes_and_nonphysical_parameters_fail_closed(
    task, old, new, error
):
    with pytest.raises(ValueError, match=error):
        changed(task, old, new)
