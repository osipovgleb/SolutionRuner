"""Nonnegative square branches and explicit primary-source condition restoration."""

import hashlib
import json
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
from solution_runner.pipelines.equations.logarithm_square_factor import analyze
from solution_runner.pipelines.equations.logarithm_square_factor_proof import SOURCES
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_square_factor_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {
    "642335": (4, X + 3, X + 2, 1),
    "642438": (5, X - 5, X - 7, 10),
    "642793": (5, X + 2, X + 1, 3),
}


def handler():
    return get_handler(get_group_profile("642335").content_rule_key)


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
def test_manual_original_domains_zero_case_and_nonpositive_log_branch(row):
    a = analyze(read_formula(canonical(row))[1])
    base, A, B, zero = MANUAL[row["task"]]
    assert (a.base, a.A, a.B) == (base, A, B)
    domain = sp.Intersection(
        *(
            sp.solve_univariate_inequality(arg > 0, X, relational=False)
            for arg in (A, A**2, B)
        )
    )
    same_set(a.domain, domain)
    same_set(a.zero_case, sp.FiniteSet(zero))
    same_set(
        a.log_case,
        sp.solve_univariate_inequality(B <= 1, X, relational=False).intersect(domain),
    )
    same_set(
        a.solution,
        sp.solve_univariate_inequality(
            (A - base) ** 2 * (B - 1) <= 0, X, relational=False
        ).intersect(domain),
    )
    same_set(a.solution, answer_set(row["expected_answer"]))
    same_set(answer_set(plan(row).answer), a.solution)
    assert (
        a.solution.contains(zero) is sp.true and a.log_case.contains(zero) is sp.false
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_reciprocal_base_and_polynomial_argument_values(row):
    a = analyze(read_formula(canonical(row))[1])
    base, A, B, zero = MANUAL[row["task"]]
    points = [sp.Rational(n, 4) for n in range(-12, 49)] + [sp.Integer(zero)]
    for point in points:
        if a.domain.contains(point) is not sp.true:
            assert a.solution.contains(point) is sp.false
            continue
        av, bv = A.subs(X, point), B.subs(X, point)
        value = (
            (
                (sp.log(av) / sp.log(sp.Rational(1, base))) ** 2
                - sp.log(sp.expand(A**2).subs(X, point)) / sp.log(base)
                + 1
            )
            * sp.log(bv)
            / sp.log(base)
        )
        value = sp.N(sp.simplify(value), 40)
        assert bool(a.solution.contains(point)) == bool(value <= 0)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_plan_has_visible_condition_fix_only_for_verified_damaged_source(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == original and p.condition_html == row["expected_condition_html"]
    assert "<img" not in p.solution_html and not handler().diagram_specs(ctx)
    assert "\\" not in BeautifulSoup(p.solution_html, "html.parser").get_text()
    assert p.solution_html.index("сначала учитываем") < p.solution_html.index(
        "x=" + str(MANUAL[row["task"]][3])
    )
    condition_changes = [
        t
        for t in p.transformations
        if t["transformation_target_id"].startswith("section:condition")
    ]
    assert len(condition_changes) == (1 if row["task"] == "642793" else 0)
    if condition_changes:
        assert p.transformations[0] == condition_changes[0]
        assert condition_changes[0]["value"]["html"] == row["expected_condition_html"]
    assert all(
        t["transformation_target_id"].startswith(
            ("section:condition", "section:answer", "section:solution")
        )
        for t in p.transformations
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
    assert (
        ctx["normalized_content"]["assets"] == original["normalized_content"]["assets"]
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_cannot_control_condition_transcription_or_solution(row):
    ctx = deepcopy(row["context"])
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] == "answer":
            section["html"] = "<p>999</p>"
    p = plan(row, ctx)
    same_set(answer_set(p.answer), answer_set(row["expected_answer"]))
    assert p.condition_html == row["expected_condition_html"]
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой родитель.</p>")


def test_reviewed_transcription_is_exact_and_restores_only_the_missing_square():
    row = ROWS[-1]
    entry = next(iter(SOURCES["condition_transcriptions"].values()))
    before = next(
        s["html"]
        for s in row["context"]["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    assert (
        entry["source_problem_id"] == "642793"
        and entry["source_url"] == "https://math-ege.sdamgia.ru/problem?id=642793"
    )
    assert hashlib.sha256(before.encode()).hexdigest() == entry["condition_sha256"]
    assert (
        before == entry["before_html"]
        and entry["after_html"]
        == before.replace(r"\log_{0,2}(x+2)", r"\log_{0,2}^{2}(x+2)", 1)
        == row["expected_condition_html"]
    )
    with pytest.raises(UnsupportedCondition):
        analyze(read_formula(row["context"])[1])
    # The missing square changes the problem; this cannot be a silent parse alias.
    u = sp.log(3) / sp.log(5)
    v = sp.log(2) / sp.log(5)
    assert sp.N((1 - 3 * u) * v, 40) < 0 and sp.N((u - 1) ** 2 * v, 40) > 0


@pytest.mark.parametrize("mutation", ["whitespace", "argument", "instruction"])
def test_unknown_damaged_condition_fingerprint_is_not_guessed(mutation):
    row = ROWS[-1]
    ctx = deepcopy(row["context"])
    section = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    if mutation == "whitespace":
        section["html"] = section["html"].replace("(x+2)", "(x +2)", 1)
    elif mutation == "argument":
        section["html"] = section["html"].replace("(x+2)", "(x+3)", 1)
    else:
        section["html"] += "<p>Округлите ответ.</p>"
    original = deepcopy(ctx)
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
    assert ctx == original


def test_canonical_square_with_different_spacing_needs_no_repair():
    row = ROWS[-1]
    ctx = canonical(row)
    condition = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    condition["html"] = condition["html"].replace("(x+2)", "(x +2)", 1)
    p = plan(row, ctx)
    assert p.condition_html == condition["html"]
    assert not any(
        t["transformation_target_id"].startswith("section:condition")
        for t in p.transformations
    )


def test_hidden_hole_excludes_the_square_zero_even_after_argument_cancellation():
    a = analyze(
        r"(\log_{0.25}^2\frac{(x+3)(x-1)}{x-1}-\log_4(x^2+6x+9)+1)\log_4(x+2)\le0"
    )
    assert a.zero_case is sp.EmptySet and a.solution.contains(1) is sp.false
    same_set(a.solution, sp.Interval.Lopen(-2, -1))


def test_unreviewed_assets_are_rejected():
    row = ROWS[0]
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = [
        {"asset_id": "unknown", "asset_key": "image_1"}
    ]
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


@pytest.mark.parametrize(
    "formula",
    [
        r"(\log_{0.25}(x+3)-\log_4(x^2+6x+9)+1)\log_4(x+2)\le0",
        r"(\log_{0.25}^2(x+3)-\log_4(x^2+6x+8)+1)\log_4(x+2)\le0",
        r"(\log_{0.2}^2(x+3)-\log_4(x^2+6x+9)+1)\log_4(x+2)\le0",
        r"(\log_{0.25}^2(x+3)-\log_4(x^2+6x+9)+1)\log_4(x+2)+x\le0",
        r"(\log_{0.25}^2(x+3)-\log_4(x^2+6x+9)+1)\log_4(x+2)<0",
        r"(2\log_{0.25}^2(x+3)-\log_4(x^2+6x+9)+1)\log_4(x+2)\le0",
    ],
)
def test_entire_square_argument_reference_base_expression_and_operator_are_required(
    formula,
):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)
