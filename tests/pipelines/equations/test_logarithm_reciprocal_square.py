"""Two exact methods, primary condition repairs and read-only replay for every source."""

import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_exam_trigonometric import replay
from test_exponential_inequality_preimages import answer_set
from test_exponential_inequality_quadratic import same_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import (
    _context_fingerprint,
    _prepared_record,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.logarithm_reciprocal_square import analyze
from solution_runner.pipelines.equations.logarithm_reciprocal_square_proof import (
    SOURCES,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_reciprocal_square_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)


def handler():
    return get_handler(get_group_profile("508392").content_rule_key)


def plan(row, context=None, parent=PARENT):
    return handler().plan(
        PlanInput(
            row["context"] if context is None else context, parent_solution_html=parent
        )
    )


def canonical(row):
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition")[
        "html"
    ] = row["expected_condition_html"]
    return ctx


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_original_log_values_domains_and_independent_square_identities(row):
    a = analyze(read_formula(canonical(row))[1])
    shift = 1 if row["task"] == "511586" else -1
    root = sp.Rational(1, 3) if shift == 1 else sp.S.One
    same_set(
        a.domain,
        sp.Interval.open(-sp.Rational(shift, 3), sp.oo)
        - sp.FiniteSet(sp.Rational(1 - shift, 3)),
    )
    same_set(a.solution, sp.FiniteSet(root))
    same_set(answer_set(plan(row).answer), sp.FiniteSet(root))
    coefficient = 4 if shift == 1 else 2
    assert a.coefficient == coefficient and a.constant == 2 * coefficient - 2
    z = sp.Symbol("z", nonzero=True)
    original = z**2 + z**-2 - coefficient * z - coefficient / z + 2 * coefficient - 2
    square = (
        (z - 1) ** 2 + (1 / z - 1) ** 2 if coefficient == 2 else (z + 1 / z - 2) ** 2
    )
    assert sp.cancel(original - square) == 0
    for point in [sp.Rational(i, 9) for i in range(-9, 37)]:
        argument = 3 * point + shift
        if argument <= 0 or argument == 1:
            assert not a.domain.contains(point)
            continue
        first = math.log(float(argument), 2)
        second = math.log(2, float(argument))
        value = (
            first**2
            + second**2
            - coefficient / 2 * math.log(float(argument**2), 2)
            - coefficient / 2 * math.log(4, float(argument))
            + 2 * coefficient
            - 2
        )
        assert abs(value - float(square.subs(z, first))) < 1e-10
        assert bool(a.solution.contains(point)) == (abs(value) < 1e-10)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_both_parent_methods_explicit_repairs_readonly_runtime_and_replay(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == original and not handler().diagram_specs(ctx)
    assert (
        p.condition_html == row["expected_condition_html"]
        and "<img" not in p.solution_html
    )
    soup = BeautifulSoup(p.solution_html, "html.parser")
    sections = soup.select('section[data-content-kind="solution"]')
    assert len(sections) == 2
    assert "Пусть" in sections[0].get_text() and "Замечание" in sections[0].get_text()
    assert "выделив полные квадраты" in sections[1].get_text()
    formulas = [
        s["data-inline-latex"] for s in sections[0].select("[data-inline-latex]")
    ]
    assert any("t=" in f for f in formulas) and any("t^2-2" in f for f in formulas)
    changes = [
        t
        for t in p.transformations
        if t["transformation_target_id"].startswith("section:condition")
    ]
    assert len(changes) == (0 if row["task"] == "508392" else 1)
    if changes:
        assert (
            p.transformations[0] == changes[0]
            and changes[0]["value"]["html"] == row["expected_condition_html"]
        )
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        handler().key,
        parent_solution_html=PARENT,
    )
    assert record["status"] == "prepared" and record["transformations"] == list(
        p.transformations
    )
    assert record["input_fingerprint"] == _context_fingerprint(
        original
    ) and gateway.reads == [ctx["problem_id"]]
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_cannot_choose_transcription_or_root(row):
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), answer_set(row["expected_answer"]))
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой родитель.</p>")


def test_primary_transcriptions_change_only_the_last_complete_base_and_argument():
    assert len(SOURCES["condition_transcriptions"]) == 2
    for row in ROWS[1:]:
        before = next(
            s["html"]
            for s in row["context"]["normalized_content"]["sections"]
            if s["key"] == "condition"
        )
        digest = hashlib.sha256(before.encode()).hexdigest()
        entry = SOURCES["condition_transcriptions"][digest]
        sign = "+" if row["task"] == "511586" else "-"
        assert before == entry["before_html"] and entry["condition_sha256"] == digest
        assert (
            entry["after_html"]
            == before.replace(r"\log_3 x" + sign + "14", r"\log_{(3x" + sign + "1)} 4")
            == row["expected_condition_html"]
        )
        assert (
            entry["source_url"].endswith("id=" + row["task"])
            and len(entry["source_svg_sha256"]) == 64
        )
        with pytest.raises(UnsupportedCondition):
            analyze(read_formula(row["context"])[1])


@pytest.mark.parametrize("mutation", ["spacing", "argument", "instruction", "asset"])
def test_unreviewed_damage_or_assets_do_not_receive_a_guessed_repair(mutation):
    row = ROWS[1]
    ctx = deepcopy(row["context"])
    condition = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    if mutation == "spacing":
        condition["html"] = condition["html"].replace(r"\log_3 x-14", r"\log_3 x -14")
    elif mutation == "argument":
        condition["html"] = condition["html"].replace("(3x-1)", "(3x-2)")
    elif mutation == "instruction":
        condition["html"] += "<p>Округлите ответ.</p>"
    else:
        ctx["normalized_content"]["assets"] = [
            {"asset_id": "unknown", "asset_key": "image_1"}
        ]
    original = deepcopy(ctx)
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
    assert ctx == original


def formula(base="2", argument="3x-1", coefficient="2", constant="2"):
    scale = sp.Rational(coefficient) / 2
    return rf"\log_{{{base}}}^2({argument})+\log_{{({argument})}}^2({base})-({scale})\log_{{{base}}}({argument})^2-({scale})\log_{{({argument})}}({int(base) ** 2})+{constant}\le0"


@pytest.mark.parametrize("coefficient,constant", [("2", "2"), ("4", "6")])
def test_another_base_decreasing_affine_argument_and_correct_domain(
    coefficient, constant
):
    a = analyze(formula("5", "7-2x", coefficient, constant))
    same_set(a.domain, sp.Interval.open(-sp.oo, sp.Rational(7, 2)) - sp.FiniteSet(3))
    same_set(a.solution, sp.FiniteSet(1))


@pytest.mark.parametrize(
    "bad",
    [
        formula(constant="3"),
        formula(coefficient="3", constant="4"),
        formula(base="1"),
        formula(base="11"),
        formula(argument="x^2+1"),
        formula().replace(r"\le", "<"),
        formula().replace(r"\le0", r"+x\le0"),
        formula().replace(r"\log_{(3x-1)}^2(2)", r"\log_{(3x-2)}^2(2)"),
        formula().replace(r"\log_{2}^2(3x-1)", r"\log_{2}(3x-1)"),
        formula().replace(r"\log_{2}^2(3x-1)", r"\log_{2}^2((3x-1)x/x)"),
    ],
)
def test_complete_identity_base_arguments_operator_and_original_holes_are_checked(bad):
    with pytest.raises(UnsupportedCondition):
        analyze(bad)
