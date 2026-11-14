"""Whole original logarithms, positive factors and exact domain-clipped charts."""

import json
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_exam_trigonometric import replay
from test_exponential_inequality_preimages import answer_set
from test_exponential_inequality_quadratic import same_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import (
    _prepared_record,
    _with_required_assets,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.logarithm_polynomial_product import analyze
from solution_runner.pipelines.equations.logarithm_polynomial_product_figures import (
    SOURCES,
    render,
    signature,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_polynomial_product_sources.json")
    .read_text()
)
PARENTS = {
    r["group"]: next(
        s["html"]
        for s in r["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    for r in ROWS
    if r["task"] == r["group"]
}
MANUAL = {
    "508452": (X, X**2 - 4 * X - 5, 2, 4),
    "508454": (X, X**2 - 2 * X - 3, 5, 2),
    "511538": (X, X**2 - 3 * X - 10, 2, 1),
    "548385": (4 - X, X**2 - 10, 3, 5),
    "548404": (X + 5, X**2 - 18, 2, 9),
    "548426": (5 - X, X**2 - 6, 7, 3),
    "548480": (X + 3, X**2 - 6, 7, 3),
    "548485": (6 - X, X**2 - 8, 5, 4),
    "548487": (X - 3, X**2 - 4, 5, 2),
    "548558": (X + 2, X**2 - 8, 5, 4),
    "548565": (X - 1, X**2 - 6, 7, 3),
}


def handler(row):
    return get_handler(get_group_profile(row["group"]).content_rule_key)


def plan(row, context=None, parent=None):
    h = handler(row)
    ctx = _with_required_assets(row["context"] if context is None else context, h.key)
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
            ctx,
            parent_solution_html=PARENTS[row["group"]] if parent is None else parent,
            generated_solution_assets=generated,
        )
    )


def original_terms(task):
    A, _P, b, k = MANUAL[task]
    if task == "508452":
        return ((16, X, X**2), (16, X**5, -1), (2, X, -X))
    if task == "508454":
        return ((25, X, X**2), (25, X**3, -1), (5, X, -X))
    if task == "511538":
        return ((4, X, 2 * X**2), (2, X**5, -2), (2, X, -3 * X))
    return ((b**k, A, X**2), (b, sp.expand(A**2), -1))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_complete_source_terms_manual_domains_and_answers(row):
    a = analyze(read_formula(row["context"])[1])
    A, P, b, k = MANUAL[row["task"]]
    assert (a.argument, a.polynomial, a.base, a.scale) == (A, P, b, k)
    terms = original_terms(row["task"])
    assert all(
        atom.base == base and sp.expand(atom.argument - arg) == 0 and coefficient == c
        for atom, coefficient, (base, arg, c) in zip(
            a.atoms, a.coefficients, terms, strict=True
        )
    )
    domain = sp.Intersection(
        *(
            sp.solve_univariate_inequality(arg > 0, X, relational=False)
            for _, arg, _ in terms
        )
    )
    same_set(a.domain, domain)
    rational = P * (A - 1)
    oracle = sp.solve_univariate_inequality(
        rational >= 0 if a.operator == ">=" else rational <= 0, X, relational=False
    ).intersect(domain)
    same_set(a.solution, oracle)
    same_set(a.solution, answer_set(row["expected_answer"]))
    same_set(answer_set(plan(row).answer), a.solution)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_logarithm_values_on_both_sides_of_one_and_at_boundaries(row):
    a = analyze(read_formula(row["context"])[1])
    A, P, _, _ = MANUAL[row["task"]]
    terms = original_terms(row["task"])
    points = [sp.Rational(n, 4) for n in range(-24, 29)] + list(a.stage.points)
    for point in points:
        if a.domain.contains(point) is not sp.true:
            assert a.solution.contains(point) is sp.false
            continue
        value = sum(
            sp.sympify(c).subs(X, point) * sp.log(arg.subs(X, point)) / sp.log(base)
            for base, arg, c in terms
        )
        value = sp.N(sp.simplify(value), 40)
        if sp.simplify(P.subs(X, point)) == 0 or A.subs(X, point) == 1:
            # Evaluate exact zeros separately from cancellation noise in logarithms.
            assert abs(value) < sp.Rational(1, 10**30)
            value = sp.S.Zero
        assert bool(a.solution.contains(point)) == bool(
            value >= 0 if a.operator == ">=" else value <= 0
        )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_runtime_replay_and_preserved_original_assets(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    h = handler(row)
    assert (
        ctx == original
        and "\\" not in BeautifulSoup(p.solution_html, "html.parser").get_text()
    )
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        h.key,
        parent_solution_html=PARENTS[row["group"]],
    )
    assert (
        record["status"] == "prepared"
        and record["transformations"] == list(p.transformations)
        and gateway.reads == [ctx["problem_id"]]
    )
    assert p.solution_html.count("<img ") == (1 if row["group"] == "548385" else 0)
    assert all(
        not t["transformation_target_id"].startswith("section:condition")
        for t in p.transformations
    )
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations
    assert all(
        asset in ctx["normalized_content"]["assets"]
        for asset in original["normalized_content"]["assets"]
    )
    if row["task"] != "548487":
        assert not any(
            t["transformation_target_id"].startswith("asset:")
            for t in p.transformations
        )


@pytest.mark.parametrize(
    "row",
    [r for r in ROWS if r["context"]["normalized_content"]["assets"]],
    ids=lambda r: r["task"],
)
def test_native_charts_match_explicitly_reviewed_points_signs_and_markers(row):
    a = analyze(read_formula(row["context"])[1])
    asset = row["context"]["normalized_content"]["assets"][0]
    assert SOURCES["figures"][asset["asset_id"]]["signature"] == signature(a)
    assert not handler(row).diagram_specs(row["context"])
    if row["group"] == "548385":
        assert asset["asset_id"] in plan(row).solution_html
    else:
        assert "<img" not in plan(row).solution_html


def test_missing_chart_is_generated_in_parent_style_with_domain_boundary_open():
    row = next(r for r in ROWS if r["task"] == "548487")
    a = analyze(read_formula(row["context"])[1])
    specs = handler(row).diagram_specs(row["context"])
    assert len(specs) == 1
    root = ET.fromstring(render(a))
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert root.get("viewBox") == "0 0 215.3065 45.2688"
    circles = root.findall("s:circle", ns)
    assert [(c.get("data-boundary"), c.get("fill")) for c in circles] == [
        ("3", "#FFFFFF"),
        ("4", "#000000"),
    ]
    signs = [
        int(t.get("data-sign"))
        for t in root.findall("s:text", ns)
        if t.get("data-sign")
    ]
    assert signs == [-1, 1] and all(
        float(t.get("y")) < 45.2688 for t in root.findall("s:text", ns)
    )
    assert any(t.get("fill") == "#143B8F" for t in root.findall("s:text", ns))
    with pytest.raises(UnsupportedCondition):
        handler(row).plan(
            PlanInput(row["context"], parent_solution_html=PARENTS[row["group"]])
        )


def test_removed_native_chart_requests_exact_source_and_does_not_generate_copy():
    row = next(r for r in ROWS if r["task"] == "548385")
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = []
    prepared = _with_required_assets(ctx, handler(row).key)
    assert (
        prepared["normalized_content"]["assets"][0]["asset_id"]
        == row["context"]["normalized_content"]["assets"][0]["asset_id"]
    )
    assert not handler(row).diagram_specs(prepared)
    assert (
        row["context"]["normalized_content"]["assets"][0]["asset_id"]
        in plan(row, ctx).solution_html
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_is_not_an_input_and_parent_identity_is_required(row):
    ctx = deepcopy(row["context"])
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] == "answer":
            section["html"] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), answer_set(row["expected_answer"]))
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой метод.</p>")


@pytest.mark.parametrize(
    "field,value",
    [
        ("asset_key", "wrong"),
        ("kind", "unknown"),
        ("kind", None),
        ("url", "/wrong"),
        ("url", None),
    ],
)
def test_native_chart_requires_complete_metadata(field, value):
    row = next(r for r in ROWS if r["task"] == "548385")
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"][0][field] = value
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


def test_known_chart_of_other_mathematics_is_not_reused():
    row = next(r for r in ROWS if r["task"] == "548404")
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = deepcopy(
        next(r for r in ROWS if r["task"] == "548385")["context"]["normalized_content"][
            "assets"
        ]
    )
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


def test_original_hole_in_canceled_logarithm_argument_is_retained():
    a = analyze(r"x^2\log_{16}\frac{x(x-5)}{x-5}\ge\log_{16}x^5+x\log_2 x")
    assert a.solution.contains(5) is sp.false
    same_set(a.solution, sp.Union(sp.Interval.Lopen(0, 1), sp.Interval.open(5, sp.oo)))


@pytest.mark.parametrize(
    "formula",
    [
        r"x^2\log_{16}x\ge\log_{16}x^5+x\log_2 x+1",
        r"x^3\log_{16}x\ge\log_{16}x^5+x\log_2 x",
        r"x^2\log_{16}x\ge\log_{16}(x+1)+x\log_2 x",
        r"x^2\log_{16}^2 x\ge\log_{16}x^5+x\log_2 x",
        r"x^2\log_{16}x\ge\log_{16}x^5+x\log_3 x",
        r"x^2\log_{0.5}x\ge\log_{16}x^5+x\log_2 x",
        r"\sqrt{2}x^2\log_{16}x\ge\log_{16}x^5+x\log_2 x",
    ],
)
def test_complete_outer_expression_arguments_bases_and_degree_are_required(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)
