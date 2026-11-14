"""Both original bases, isolated equality roots and source-ordered cases."""

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

from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.logarithm_reciprocal_sum import analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_reciprocal_sum_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {
    "508456": (X + 1, 2 * X - 5, 6),
    "508553": (2 * X - 1, 4 * X - 5, 2),
    "508563": (2 * X + 1, 4 * X - 5, 3),
    "508565": (3 * X + 1, 4 * X - 6, 7),
    "511575": (4 * X + 1, 5 * X - 6, 7),
}


def handler():
    return get_handler(get_group_profile("508456").content_rule_key)


def plan(row, context=None, parent=PARENT):
    return handler().plan(
        PlanInput(
            row["context"] if context is None else context, parent_solution_html=parent
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_manual_original_domains_answers_and_equality_points(row):
    a = analyze(read_formula(row["context"])[1])
    G, A, root = MANUAL[row["task"]]
    assert sp.expand(a.G - G) == sp.expand(a.A - A) == 0
    domain = sp.Intersection(
        *(sp.solve_univariate_inequality(e > 0, X, relational=False) for e in (G, A))
    ) - sp.Union(*(sp.solveset(e - 1, X, domain=sp.S.Reals) for e in (G, A)))
    same_set(a.domain, domain)
    same_set(a.equality, sp.FiniteSet(root))
    same_set(a.solution, answer_set(row["expected_answer"]))
    assert a.negative.contains(root) is sp.false
    assert a.solution.contains(root) is sp.true
    for pole in a.poles:
        assert a.solution.contains(pole) is sp.false
    same_set(answer_set(plan(row).answer), a.solution)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_values_of_both_original_logarithms(row):
    a = analyze(read_formula(row["context"])[1])
    points = [sp.Rational(n, 12) for n in range(-12, 97)] + list(a.poles)
    for point in points:
        if a.domain.contains(point) is not sp.true:
            assert a.solution.contains(point) is sp.false
            continue
        G, A = a.G.subs(X, point), a.A.subs(X, point)
        original = sp.log(A) / sp.log(G) + sp.log(G) / sp.log(A) - 2
        value = sp.N(sp.simplify(original), 40)
        assert bool(a.solution.contains(point)) == bool(value <= 0)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_runtime_replay_and_parent_case_order(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == original and not handler().diagram_specs(ctx)
    assert "<img" not in p.solution_html
    assert "\\" not in BeautifulSoup(p.solution_html, "html.parser").get_text()
    assert p.solution_html.index("=1") < p.solution_html.index(
        "Или логарифм отрицателен"
    )
    assert p.solution_html.index("Объединим решения") < p.solution_html.index(
        "Примечание."
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
    assert gateway.reads == [ctx["problem_id"]]
    assert all(
        t["transformation_target_id"].startswith(("section:answer", "section:solution"))
        for t in p.transformations
    )
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_{x+1}(2x-5)+\log_{2x-5}(x+1)\lt2",
        r"\log_{x+1}(2x-5)+\log_{2x-5}(x+1)\le3",
        r"\log_{x+1}(2x-5)+\log_{2x-5}(x+2)\le2",
        r"\log_{x+1}(2x-5)+\log_{2x-5}(x+1)+x\le2",
        r"\log_{x^2+1}(2x-5)+\log_{2x-5}(x^2+1)\le2",
        r"\log_{x+1}(2x-5)\log_{2x-5}(x+1)\le2",
    ],
)
def test_whole_sum_reciprocal_pair_bound_and_affine_shape_are_required(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_is_not_an_input_and_parent_must_match(row):
    ctx = deepcopy(row["context"])
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] == "answer":
            section["html"] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), answer_set(row["expected_answer"]))
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой метод.</p>")
    ctx["normalized_content"]["assets"] = [
        {"asset_id": "unknown", "asset_key": "image_1"}
    ]
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


def test_hidden_original_denominator_and_unit_base_holes_are_not_reintroduced():
    a = analyze(
        r"\log_{\frac{(x+1)(x-6)}{x-6}}(2x-5)+\log_{2x-5}\frac{(x+1)(x-6)}{x-6}\le2"
    )
    assert a.equality is sp.EmptySet
    assert a.solution.contains(6) is sp.false
    same_set(a.solution, sp.Interval.open(sp.Rational(5, 2), 3))


def test_bases_on_opposite_sides_of_one_and_excluded_equality_root():
    a = analyze(r"\log_{1-x}(1+x)+\log_{1+x}(1-x)\le2")
    expected = sp.Union(sp.Interval.open(-1, 0), sp.Interval.open(0, 1))
    same_set(a.domain, expected)
    same_set(a.negative, expected)
    same_set(a.solution, expected)
    assert a.equality is sp.EmptySet
