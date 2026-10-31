"""Water speed domains, exact sailing time and parent algebraic notes."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
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

from solution_runner.pipelines.word_problems import (
    average_speed,
    math_common,
    relative_motion,
)
from solution_runner.pipelines.word_problems import motion_models as model
from solution_runner.pipelines.word_problems.water_balances import (
    CURRENT_KINDS,
    seasonal_factors,
)
from solution_runner.pipelines.word_problems.water_questions import clock_minutes, ratio

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_11_water.json").read_text()
)
CASES = DATA["cases"]


def case_for(task):
    return next(c for c in CASES if c["task"] == task)


def changed(case, old, new):
    context = deepcopy(case["context"])
    text = math_common.read(context)[3]
    assert old in text
    next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )["html"] = "<p>" + text.replace(old, new) + "</p>"
    return context


@pytest.mark.parametrize("group", DATA["groups"], ids=lambda g: g["key"])
def test_all_water_groups_extend_existing_motion_rules(group):
    verify_registration(group)
    assert group["rule"] in {
        "word-motion-time-balance",
        "word-average-speed",
        "word-relative-displacement",
    }


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_sources_replay_without_saved_answer_dependency(case):
    verify_source(case)
    if case["group"] == "99604":
        _, a = average_speed.calculate(case["context"])
        assert a.result * sum(a.times) == sum(a.distances)
        assert a.result == 2 * a.question.speeds[0] * a.question.speeds[1] / sum(
            a.question.speeds
        )
    elif case["group"] == "99610":
        _, a = relative_motion.calculate(case["context"])
        v = a.question.values
        assert 1000 * a.displacement == sum(v.values())
        assert a.result * a.question.time.total_seconds / 3600 == a.displacement
    else:
        _, a = model.calculate(case["context"])
        assert a.balance.domain.contains(a.root) is sp.true
        assert all(d.subs(model.X, a.root) != 0 for d in a.balance.denominators)
        assert (
            sp.simplify((a.balance.left - a.balance.right).subs(model.X, a.root)) == 0
        )
        assert a.balance.output.subs(model.X, a.root) == a.result


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("mode", ["leading", "trailing", "asset", "solution_reference"])
def test_extra_instructions_and_foreign_figures_fail_closed(case, mode):
    verify_rejection(case, mode)


@pytest.mark.parametrize(
    "case",
    [
        c
        for c in CASES
        if c["group"] in {"26585", "26586", "26587", "26588", "26589", "26610", "99602"}
    ],
    ids=lambda c: c["task"],
)
def test_both_sailing_speeds_are_positive_and_no_river_pole_is_selected(case):
    _, a = model.calculate(case["context"])
    q = a.question
    boat, current = (
        (q.values["known"], a.root)
        if q.kind in CURRENT_KINDS
        else (a.root, q.values["known"])
    )
    assert boat > current > 0
    distance = q.values["distance"]
    upstream, downstream = distance / (boat - current), distance / (boat + current)
    assert upstream > downstream > 0
    if q.kind.endswith("_difference"):
        assert upstream - downstream == q.durations["delay"].total
    elif q.kind == "water_raft":
        assert (
            upstream + downstream + q.durations["delay"].total
            == q.values["raft_distance"] / current
        )
    else:
        assert (
            upstream + downstream + q.durations["stop"].total
            == q.durations["elapsed"].total
        )


@pytest.mark.parametrize(
    "case",
    [c for c in CASES if c["group"] in {"26587", "26610"}],
    ids=lambda c: c["task"],
)
def test_same_day_clocks_and_mixed_hour_stops_give_exact_sailing_time(case):
    _, a = model.calculate(case["context"])
    q = a.question
    assert q.values["end_minute"] > q.values["start_minute"]
    assert (
        q.durations["moving"].total
        == (q.values["end_minute"] - q.values["start_minute"]) / 60
        - q.durations["stop"].total
    )


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["group"] == "99601"], ids=lambda c: c["task"]
)
def test_the_requested_entire_cruise_is_twice_the_solved_half_distance(case):
    _, a = model.calculate(case["context"])
    assert a.result == 2 * a.root
    v = a.question.values
    assert (
        a.root / (v["boat"] - v["current"]) + a.root / (v["boat"] + v["current"])
        == a.question.durations["moving"].total
    )
    assert (
        f"2S=2\\cdot{math_common.number(a.root)}={math_common.number(a.result)}"
        in plan(case).solution_html
    )


@pytest.mark.parametrize(
    "task", ["26585", "5703", "39361", "505150", "99602", "115023", "115027", "562755"]
)
def test_half_discriminant_formula_and_parent_note_remain_mathematically_correct(task):
    case = case_for(task)
    _, a = model.calculate(case["context"])
    html = plan(case).solution_html
    assert "Примечание" in html and "чётн" in html
    assert r"(\frac{b}{2})^2-ac" in html
    poly = sp.Poly(a.polynomial, model.X)
    if poly.nth(1) % 2:
        poly *= 2
    half = poly.nth(1) / 2
    reduced = half**2 - poly.nth(2) * poly.nth(0)
    assert sp.sqrt(reduced).is_Integer
    assert {(-half + sign * sp.sqrt(reduced)) / poly.nth(2) for sign in [-1, 1]} == set(
        a.roots
    )
    if task in {"99602", "115023", "115027", "562755"}:
        assert "квадрат суммы" in html
        assert f"\\sqrt{{{reduced}}}" in html


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["group"] == "26589"], ids=lambda c: c["task"]
)
def test_vieta_note_updates_both_roots_sum_and_product(case):
    _, a = model.calculate(case["context"])
    poly = sp.Poly(a.polynomial, model.X)
    first, second = a.roots
    assert first + second == -poly.nth(1) / poly.nth(2)
    assert first * second == -(a.question.values["known"] ** 2)
    html = plan(case).solution_html
    assert "обратной теореме Виета" in html
    assert f"u_1u_2={math_common.number(first * second)}=" in html


@pytest.mark.parametrize(
    "task,wants_boat,expected", [("500253", False, 5), ("654662", True, 12)]
)
def test_seasonal_speed_table_and_actual_requested_quantity(task, wants_boat, expected):
    case = case_for(task)
    _, a = model.calculate(case["context"])
    q = a.question
    factor, _ = seasonal_factors(q)
    current, boat = a.root, factor * a.root
    gap = q.values["gap"]
    assert boat > current > gap > 0
    assert (boat + current) / (boat - current) == q.values["spring_ratio"]
    assert (boat + current - gap) / (boat - current + gap) == q.values["summer_ratio"]
    assert a.result == expected == (boat if wants_boat else current)
    table = BeautifulSoup(plan(case).solution_html, "html.parser").find("table")
    assert len(table.find_all("tr")) == 3
    assert (
        "Скорость весной" in table.get_text() and "Скорость летом" in table.get_text()
    )
    assert "По течению" in table.get_text() and "Против течения" in table.get_text()


@pytest.mark.parametrize(
    "text,expected",
    [
        (r"1\frac{2}{3}", sp.Rational(5, 3)),
        (r"1\frac{2}{5}", sp.Rational(7, 5)),
        ("2", sp.Integer(2)),
    ],
)
def test_mixed_speed_ratios_are_parsed_as_exact_rationals(text, expected):
    assert ratio(text) == expected


@pytest.mark.parametrize("text", [r"1\frac{2}{0}", r"1\frac{3}{2}", r"1\frac{0}{2}"])
def test_noncanonical_mixed_speed_ratios_fail_closed(text):
    with pytest.raises(ValueError, match="proper nonzero fractional part"):
        ratio(text)


@pytest.mark.parametrize("text", ["24:00", "12:60", "25:01"])
def test_invalid_departure_or_return_clock_times_fail_closed(text):
    with pytest.raises(ValueError, match="valid departure"):
        clock_minutes(text)


@pytest.mark.parametrize(
    "task,old,new,error",
    [
        ("26585", "11 км/ч", "0 км/ч", "positive water"),
        ("26585", "на 6 часов меньше", "на 6 часов больше", "complete road-motion"),
        ("26586", "255 км", "256 км", "exact rational"),
        ("26587", "18:00", "09:00", "same-day arrival"),
        ("26587", "18:00", "24:00", "valid departure"),
        ("26587", "2 часа 30 минут", "9 часов", "positive sailing time"),
        ("26587", "лодка отправилась", "баржа отправилась", "consistent vessel"),
        ("26588", "10 часов", "40 часов", "positive sailing time"),
        ("26590", "1 час после", "0 часов после", "positive duration"),
        ("26610", "16:00", "09:00", "same-day arrival"),
        ("99601", "3 км/ч", "25 км/ч", "boat must be faster"),
        ("99602", "24 км", "2 км", "positive sailing time"),
        ("500253", r"1\frac{1}{2}", "2", "spring ratio must exceed"),
        ("654662", r"1\frac{2}{5}", "1", "spring ratio must exceed"),
        ("680570", "36 минут", "36 секунд", "complete road-motion"),
        ("99604", "20 км/ч", "0 км/ч", "positive leg speeds"),
        ("99610", "12 минут", "0 минут", "positive short duration"),
        ("99610", "от кормы первого", "от носа первого", "complete relative-motion"),
    ],
)
def test_nonphysical_values_and_changed_directions_units_or_instructions_fail_closed(
    task, old, new, error
):
    case = case_for(task)
    with pytest.raises(ValueError, match=error):
        plan(case, changed(case, old, new))
