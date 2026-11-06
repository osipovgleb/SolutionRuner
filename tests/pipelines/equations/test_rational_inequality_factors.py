"""Positive quadratic factors and common squares keep exact zeros, domains and charts."""

import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_exam_trigonometric import replay
from test_rational_inequality import answer_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import (
    _prepared_record,
    _with_required_assets,
)
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.rational_inequality import analyze
from solution_runner.pipelines.equations.rational_inequality_factor_methods import (
    positive_quadratics,
    square_parameters,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read
from solution_runner.pipelines.equations.rational_inequality_hatched_svg import (
    double_zero,
)
from solution_runner.pipelines.equations.rational_inequality_methods import prepare
from solution_runner.pipelines.equations.rational_inequality_parser import (
    RationalParser,
    X,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition

SOURCES = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("rational_inequality_factor_sources.json")
    .read_text()
)
METHODS = {"530457": "quartic_cancel", "635864": "common_square"}


def handler(row):
    return get_handler(
        "exam-rational-inequality-" + METHODS[row["group"]].replace("_", "-")
    )


def parent(row):
    return next(
        s["html"]
        for r in SOURCES
        if r["task"] == row["group"]
        for s in r["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def plan(row, ctx):
    h = handler(row)
    ctx = _with_required_assets(ctx, h.key)
    generated = tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in h.diagram_specs(ctx)
    )
    return h.plan(
        PlanInput(
            ctx, parent_solution_html=parent(row), generated_solution_assets=generated
        )
    )


def expected(row):
    return answer_set(row["expected_answer"].replace("{,}", "."))


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_native_answers_and_all_factored_steps_match_an_independent_cas(row):
    a = read(row["context"])[1]
    relation = {"<=": sp.Le, ">=": sp.Ge}[a.operator]
    independent = sp.solve_univariate_inequality(
        relation(a.original, 0), X, relational=False
    ) - sp.FiniteSet(*a.poles)
    assert a.solution == independent == expected(row)
    _, steps = prepare(a, METHODS[row["group"]])
    for st in steps:
        assert sp.cancel(RationalParser(st.text).parse().value - a.original) == 0
    assert answer_set(plan(row, row["context"]).answer) == independent


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_exact_native_reuse_replay_and_read_only_gateway(row):
    ctx = deepcopy(row["context"])
    p = plan(row, ctx)
    assert ctx == row["context"]
    assert not handler(row).diagram_specs(ctx)
    assert all(
        not t["transformation_target_id"].startswith("section:condition")
        for t in p.transformations
    )
    for asset in ctx["normalized_content"].get("assets", []):
        assert asset["asset_id"] in p.solution_html
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        handler(row).key,
        parent_solution_html=parent(row),
    )
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == p.answer and record["transformations"] == list(
        p.transformations
    )
    assert len(gateway.reads) == 1 and gateway.ctx == ctx
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


@pytest.mark.parametrize(
    "row", [r for r in SOURCES if r["group"] == "530457"], ids=lambda r: r["task"]
)
def test_irreducible_quadratic_positivity_is_proved_only_when_it_exists(row):
    a = read(row["context"])[1]
    factors = positive_quadratics(a)
    html = plan(row, row["context"]).solution_html
    assert len(factors) == (0 if row["task"] == "530559" else 1)
    assert bool(factors) == ("Квадратный множитель положителен" in html)
    for factor, completed in factors:
        assert sp.expand(factor - completed) == 0
        assert sp.discriminant(sp.Poly(factor, X)) < 0
        assert sp.Poly(factor, X).LC() > 0
        for value in (factor, completed):
            assert (
                sp.expand(RationalParser(sp.latex(value)).parse().value - factor) == 0
            )
    assert a.holes and all(h not in a.solution for h in a.holes)


@pytest.mark.parametrize(
    "row", [r for r in SOURCES if r["group"] == "635864"], ids=lambda r: r["task"]
)
def test_common_square_zero_is_an_isolated_solution_and_never_cancelled(row):
    a = read(row["context"])[1]
    n, d, extra, zero = square_parameters(a)
    assert sp.cancel(n / d * (1 - 1 / extra) - a.original) == 0
    assert sp.FiniteSet(zero) in a.solution.args
    assert double_zero(a) == zero
    assert "Общий квадрат не сокращаем" in plan(row, row["context"]).solution_html


def modified_context(formula):
    row = next(r for r in SOURCES if r["task"] == "635864")
    ctx = deepcopy(row["context"])
    section = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    soup = BeautifulSoup(section["html"], "html.parser")
    soup.span["data-inline-latex"] = formula
    section["html"] = str(soup)
    return row, ctx


@pytest.mark.parametrize(
    "formula,zero,height",
    [
        (
            r"\frac{(3x-5)^2}{x-3}\ge\frac{25-30x+9x^2}{x^2-8x+15}",
            sp.Rational(5, 3),
            "54.6595",
        ),
        (
            r"\frac{(x-10)^2}{x-3}\ge\frac{x^2-20x+100}{x^2-8x+15}",
            sp.Integer(10),
            "54.6595",
        ),
        (
            r"\frac{(3x-4)^2}{x-3}>\frac{16-24x+9x^2}{x^2-8x+15}",
            sp.Rational(4, 3),
            "54.6595",
        ),
    ],
)
def test_adapted_hatched_diagram_keeps_multiplicity_selected_intervals_and_strictness(
    formula, zero, height
):
    row, ctx = modified_context(formula)
    a = read(ctx)[1]
    (spec,) = handler(row).diagram_specs(ctx)
    root = ET.fromstring(spec["svg_text"])
    assert root.get("width") == "236.3568" and root.get("height") == height
    annotation = next(n for n in root.iter() if n.get("data-multiplicity"))
    assert (
        annotation.get("data-multiplicity") == "2"
        and annotation.get("data-zero") == str(zero)
        and annotation.text == "кратн. 2"
    )
    marks = {n.get("data-boundary"): n for n in root.iter() if n.get("data-boundary")}
    assert marks[str(zero)].get("fill") == (
        "#000000" if a.operator.endswith("=") else "#FFFFFF"
    )
    assert all(marks[str(p)].get("fill") == "#FFFFFF" for p in a.poles)
    selected = [
        int(n.get("data-selected-interval"))
        for n in root.iter()
        if n.get("data-selected-interval")
    ]
    assert selected == [i for i, sign in enumerate(a.signs) if sign > 0]
    assert any(n.get("stroke") == "#143B8F" for n in root.iter())
    assert answer_set(plan(row, ctx).answer) == a.solution


@pytest.mark.parametrize(
    "formula,method",
    [
        (r"\frac{x^4+1}{x^2-1}-\frac{x^3}{x+1}\le1", "quartic_cancel"),
        (r"\frac{(x-2)^2}{x-3}\ge\frac{x^2-4x+5}{(x-3)(x-5)}", "common_square"),
        (r"\frac{(x-3)^2}{x-3}\ge\frac{(x-3)^2}{(x-3)(x-5)}", "common_square"),
    ],
)
def test_unproved_factorizations_and_domain_coincidences_fail_closed(formula, method):
    with pytest.raises(UnsupportedCondition):
        prepare(analyze(formula), method)
