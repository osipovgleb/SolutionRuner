"""Binary-log source replays, half-life repairs and strict physical boundaries."""

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

from solution_runner.pipelines.applied import common, log_questions
from solution_runner.pipelines.applied import log_models as model

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_10_logs.json").read_text()
)
CASES = DATA["cases"]


def sample(task):
    return next(c for c in CASES if c["task"] == task)


def changed(task, old, new):
    text = common.read(sample(task)["context"])[3]
    assert old in text
    return model.analyze(log_questions.parse(text.replace(old, new)))


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_all_five_groups_use_one_binary_log_rule(group):
    verify_registration(group)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_source_replays_are_exact_independent_and_idempotent(case):
    verify_source(case)
    _, a = model.calculate(case["context"])
    q = a.question
    v = q.values
    if q.kind == "decay":
        assert v["initial"] * 2 ** (-a.result / q.scale) == v["target"]
    elif q.kind == "bell_pressure":
        assert a.result / v["initial"] == 2**a.exponent
    else:
        offset = v.get("offset", 0)
        assert (
            a.result > offset
            and (v["initial"] - offset) / (a.result - offset) == 2**a.exponent
        )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("leading", [True, False])
def test_extra_instructions_and_assets_cannot_be_silently_ignored(case, leading):
    verify_rejection(case, leading)


@pytest.mark.parametrize("task,periods", [("42793", 7), ("42831", 3), ("42837", 2)])
def test_malformed_half_life_formula_is_repaired_without_using_saved_answers(
    task, periods
):
    case = sample(task)
    _, a = model.calculate(case["context"])
    assert a.question.repair_decay and a.exponent == periods
    result = plan(case, case["context"])
    repair = next(
        t
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:condition")
    )
    soup = BeautifulSoup(repair["value"]["html"], "html.parser")
    formulas = [n["data-inline-latex"] for n in soup.select("[data-inline-latex]")]
    assert "m(t)=" + log_questions.DECAY_LAW in formulas
    html = solution(result)
    assert "За каждый период полураспада" in html and r"\longrightarrow" in html


def test_capacitor_unique_voltage_respects_the_requested_maximum_and_zero_time():
    _, parent = model.calculate(sample("27994")["context"])
    _, child = model.calculate(sample("28463")["context"])
    assert not parent.question.maximum and child.question.maximum
    html = solution(plan(sample("27994"), sample("27994")["context"]))
    assert r"10^{-6}" in html and r"10^{6}" in html
    assert changed("27994", "прошла 21", "прошла 0").result == 16
    assert changed("27995", "равна 84 м", "равна 0 м").result == 60
    assert changed("27996", "10 350 Дж", "0 Дж").result == 8
    assert changed("27997", "6900 Дж", "0 Дж").result == sp.Rational(3, 2)


def test_water_cools_toward_room_temperature_with_equivalent_heat_units():
    _, a = model.calculate(sample("27995")["context"])
    _, b = model.calculate(sample("28477")["context"])
    assert a.question.scale == 42 and a.result == 30
    assert b.question.scale == 140 and b.result == 55
    assert a.question.values["offset"] < a.result <= a.question.values["initial"]
    negative = changed("27995", "20\\,°\\mathrm{C}", "-40\\,°\\mathrm{C}")
    assert negative.result == -15
    with pytest.raises(ValueError, match="offset"):
        changed("27995", "20\\,°\\mathrm{C}", "60\\,°\\mathrm{C}")


def test_logarithm_base_law_and_original_poles_are_checked():
    with pytest.raises(ValueError, match="binary logarithm"):
        changed("27994", r"\log_{(2)}", r"\log_{(3)}")
    with pytest.raises(ValueError, match="contradicts"):
        changed("27996", r"\frac{V_1}{V_2}", r"\frac{V_2}{V_1}")
    with pytest.raises(ValueError, match="vanishes"):
        changed("27994", r"\alpha RC", r"\alpha RC\frac{U-1}{U-1}")
    with pytest.raises(ValueError, match="half-life law"):
        changed("27991", r"2^{-\frac{t}{T}}", r"3^{-\frac{t}{T}}")


def test_pressure_domain_does_not_merge_the_inequality_command_with_its_variable():
    html = solution(plan(sample("27997"), sample("27997")["context"]))
    assert r"\leqp" not in html and r"\leq p_2" in html


def test_fractional_powers_and_logarithms_are_not_silently_rounded():
    with pytest.raises(ValueError, match="rational"):
        changed("27994", "прошла 21", "прошла 1")
    with pytest.raises(ValueError, match="rational"):
        changed("27991", "равна 5 мг", "равна 3 мг")
    assert changed("27991", "равна 5 мг", "равна 40 мг").result == 0
    with pytest.raises(ValueError, match="increase"):
        changed("27991", "равна 5 мг", "равна 80 мг")


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("27994", "прошла 21", "прошла -1"),
        ("27996", "10 350 Дж", "-1 Дж"),
        ("27991", "составляет 10", "составляет 0"),
        ("27991", "равна 5 мг", "равна 0 мг"),
        ("27994", r"\alpha=0{,}7", r"\alpha=0"),
    ],
)
def test_nonpositive_parameters_and_negative_progress_are_refused(task, old, new):
    with pytest.raises(ValueError, match="positive"):
        changed(task, old, new)
