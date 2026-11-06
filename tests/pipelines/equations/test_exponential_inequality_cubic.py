"""Triple exponential zeros, double original poles and source-style charts."""

import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from itertools import pairwise
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_exam_trigonometric import replay
from test_exponential_inequality_quadratic import answer_set, same_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import (
    _prepared_record,
    _with_required_assets,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exponential_inequality_cubic_figures import (
    KEY,
    SOURCES,
    chart,
    diagram_specs,
    required_assets,
    row_signature,
)
from solution_runner.pipelines.equations.exponential_inequality_factorizations import (
    cube_over_square,
)
from solution_runner.pipelines.equations.exponential_inequality_parser import (
    ExponentialParser,
)
from solution_runner.pipelines.equations.rational_inequality import analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_hatched_svg import (
    cubic_points,
    render_cubic,
)
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("exponential_inequality_cubic_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
RULE = "exam-exponential-inequality-cube_over_square"


def model(row):
    return cube_over_square(read_formula(row["context"])[1])


def prepared(context):
    context = _with_required_assets(context, RULE)
    generated = tuple(
        {
            **spec,
            "source_asset_id": "preview-" + spec["sha256"][:16],
            "url": "/assets/preview-" + spec["sha256"][:16],
        }
        for spec in diagram_specs(context)
    )
    return context, generated


def plan(row, context=None, parent=PARENT):
    ctx, generated = prepared(context or row["context"])
    return get_handler(RULE).plan(
        PlanInput(ctx, parent_solution_html=parent, generated_solution_assets=generated)
    )


def zero(expression):
    assert sp.simplify(sp.expand(expression.rewrite(sp.exp))) == 0


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_native_source_answers_exact_cubes_and_independent_cas(row):
    a = model(row)
    n = a.numerator
    t = n.base**n.exponent
    r = n.stage.zeros[0]
    zero(n.original - n.stage.original.subs(X, t))
    zero(n.stage.original - sp.Poly(n.stage.original, X).LC() * (X - r) ** 3)
    zero(a.denominator - a.denominator_scalar * a.denominator_factor**2)
    zero(n.base**a.level - r)
    zero(n.exponent.subs(X, a.zero) - a.level)
    assert a.denominator_scalar > 0 and sp.Poly(n.stage.original, X).LC() > 0
    relation = {"<=": sp.Le, ">=": sp.Ge, "<": sp.Lt, ">": sp.Gt}[a.operator]
    independent = sp.solve_univariate_inequality(
        relation(
            sp.sign(sp.diff(n.exponent, X)) * (X - a.zero) ** 3 / a.denominator, 0
        ),
        X,
        relational=False,
    )
    same_set(a.solution, independent)
    same_set(a.solution, answer_set(row["expected_answer"]))
    same_set(answer_set(plan(row).answer), a.solution)
    assert a.stage.poles == (a.pole,) and a.pole not in a.solution
    assert sp.diff(a.stage.original, X).subs(X, a.zero) == 0
    assert sp.diff(a.stage.original, X, 2).subs(X, a.zero) == 0
    assert sp.diff(a.stage.original, X, 3).subs(X, a.zero) != 0


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_interval_signs_match_the_actual_original_fraction(row):
    a = model(row)
    signs = []
    for lo, hi in pairwise((-sp.oo, *a.stage.points, sp.oo)):
        sample = hi - 1 if lo == -sp.oo else lo + 1 if hi == sp.oo else (lo + hi) / 2
        value = sp.N(a.original.subs(X, sample), 80)
        assert value.is_real and abs(value) > sp.Rational(1, 10**30)
        signs.append(int(sp.sign(value)))
    assert tuple(signs) == a.stage.signs


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_unconditional_displayed_identities_keep_the_positive_scalars(row):
    count = 0
    for span in BeautifulSoup(plan(row).solution_html, "html.parser").find_all(
        attrs={"data-inline-latex": True}
    ):
        text = span["data-inline-latex"]
        if "=" not in text or r"\iff" in text or r"\quad" in text:
            continue
        left, right = text.split("=")
        if right.strip() == "0":
            continue
        zero(
            ExponentialParser(left).parse().value
            - ExponentialParser(right).parse().value
        )
        count += 1
    assert count >= 4
    assert "положительный коэффициент" in plan(row).solution_html


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_source_reuse_or_local_new_chart_and_readonly_runtime(row):
    ctx = deepcopy(row["context"])
    p = plan(row, ctx)
    h = get_handler(RULE)
    assert get_group_profile("681213").content_rule_key == RULE
    assert ctx == row["context"]
    assert all(
        not t["transformation_target_id"].startswith("section:condition")
        for t in p.transformations
    )
    if ctx["normalized_content"]["assets"]:
        assert not h.diagram_specs(ctx)
        asset = ctx["normalized_content"]["assets"][0]
        assert asset["asset_id"] in p.solution_html
        assert all(
            SOURCES["figures"][asset["asset_id"]][k] == v
            for k, v in row_signature(model(row).stage).items()
        )
        assert all(
            not t["transformation_target_id"].startswith("asset:")
            for t in p.transformations
        )
    else:
        assert len(h.diagram_specs(ctx)) == 1
        assert any(
            t["transformation_target_id"] == "asset:" + KEY for t in p.transformations
        )
        assert p.solution_html.count("<img ") == 1
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        RULE,
        parent_solution_html=PARENT,
    )
    assert record["status"] == "prepared", record
    assert (
        record["transformations"] == list(p.transformations)
        and record["expected_answer"] == p.answer
    )
    assert gateway.reads == [ctx["problem_id"]] and gateway.ctx == ctx
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_prepared_svg_encodes_exact_poles_zeros_multiplicities_and_selected_intervals(
    row,
):
    a = model(row).stage
    root = ET.fromstring(render_cubic(a))
    circles = [n for n in root.iter() if n.tag.endswith("circle")]
    assert len(circles) == 2
    for node in circles:
        point = sp.Rational(node.get("data-boundary"))
        assert (node.get("fill") == "#000000") == (
            point not in a.poles and a.sign_operator.endswith("=")
        )
    labels = [n for n in root.iter() if n.get("data-multiplicity")]
    assert {
        (n.get("data-zero"), n.get("data-multiplicity"))
        for n in labels
        if n.get("data-zero")
    } == {(str(a.zeros[0]), "3")}
    assert {
        (n.get("data-pole"), n.get("data-multiplicity"))
        for n in labels
        if n.get("data-pole")
    } == {(str(a.poles[0]), "2")}
    assert [int(n.get("data-sign")) for n in root.iter() if n.get("data-sign")] == list(
        a.signs
    )
    selected = [
        int(n.get("data-selected-interval"))
        for n in root.iter()
        if n.get("data-selected-interval")
    ]
    expected = (
        [i for i, sign in enumerate(a.signs) if sign <= 0]
        if a.sign_operator in ("<", "<=")
        else [i for i, sign in enumerate(a.signs) if sign >= 0]
    )
    assert selected == expected
    assert float(root.get("height")) >= 63


@pytest.mark.parametrize("op", ["<", ">"])
def test_strict_comparison_excludes_triple_zero_and_double_pole(op):
    formula = read_formula(ROWS[0]["context"])[1].replace(r"\le", op)
    a = cube_over_square(formula)
    assert a.zero not in a.solution and a.pole not in a.solution
    root = ET.fromstring(render_cubic(a.stage))
    assert all(
        n.get("fill") == "#FFFFFF" for n in root.iter() if n.tag.endswith("circle")
    )


def test_decreasing_original_exponent_and_negative_base_weight():
    formula = r"\frac{(\frac{1}{3})^{3x}-9(\frac{1}{3})^{2x}+27(\frac{1}{3})^{x}-27}{(x+2)^2}\ge 0"
    a = cube_over_square(formula)
    assert a.zero == -1 and a.pole == -2
    assert a.solution == sp.Interval(-sp.oo, -1) - sp.FiniteSet(-2)


@pytest.mark.parametrize(
    "formula",
    [
        r"\frac{27^x-9^{x+1}+3^{x+3}-26}{(x+1)^2}\ge 0",
        r"\frac{27^x-9^{x+1}+3^{x+3}-27}{-(x+1)^2}\ge 0",
        r"\frac{27^x-9^{x+1}+3^{x+3}-27}{x^2+1}\ge 0",
        r"\frac{27^x-9^{x+1}+3^{x+3}-27}{x+1}\ge 0",
        r"\frac{27^x-9^{x+1}+3^{x+3}-27}{(x-1)^2}\ge 0",
        r"\frac{27^x-9^{x+1}+3^{x+3}-27}{(x+1)^2}\ge 1",
        r"\frac{27^{x^2}-9^{x^2+1}+3^{x^2+3}-27}{(x+1)^2}\ge 0",
    ],
)
def test_unreviewed_algebra_or_chart_multiplicities_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        cube_over_square(formula)


@pytest.mark.parametrize(
    "formula",
    [
        r"\frac{(x-1)^2}{(x+1)^2}\ge 0",
        r"\frac{(x-1)^3}{x+1}\ge 0",
        r"\frac{(x-1)^3}{(x-1)^2}\ge 0",
    ],
)
def test_generator_never_invents_multiplicities(formula):
    with pytest.raises(UnsupportedCondition):
        cubic_points(analyze(formula))


@pytest.mark.parametrize(
    "field,value",
    [
        ("asset_id", "unknown"),
        ("asset_key", "wrong"),
        ("kind", "wrong"),
        ("url", "/assets/other"),
    ],
)
def test_unknown_or_relabelled_source_chart_rejected(field, value):
    ctx = deepcopy(ROWS[0]["context"])
    ctx["normalized_content"]["assets"][0][field] = value
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)


def test_duplicate_source_chart_and_foreign_parent_rejected():
    ctx = deepcopy(ROWS[0]["context"])
    ctx["normalized_content"]["assets"] *= 2
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], parent=PARENT + "wrong")


def test_known_style_with_changed_math_gets_a_new_correct_chart():
    ctx = deepcopy(ROWS[2]["context"])
    asset = deepcopy(ROWS[0]["context"]["normalized_content"]["assets"][0])
    ctx["normalized_content"]["assets"] = [asset]
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition")[
        "asset_keys"
    ] = []
    assert len(diagram_specs(ctx)) == 1
    p = plan(ROWS[2], ctx)
    assert asset["asset_id"] not in p.solution_html and "preview-" in p.solution_html


def test_missing_exact_native_chart_selects_existing_id_and_duplicate_generated_is_rejected():
    row = ROWS[0]
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = []
    for s in ctx["normalized_content"]["sections"]:
        s["asset_keys"] = []
    needed = required_assets(ctx)
    assert (
        needed[0]["source_asset_id"]
        == row["context"]["normalized_content"]["assets"][0]["asset_id"]
    )
    assert not get_handler(RULE).diagram_specs(_with_required_assets(ctx, RULE))
    p = plan(row, ctx)
    assert needed[0]["source_asset_id"] in p.solution_html
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"].append(
        {"asset_key": KEY, "asset_id": "unexpected"}
    )
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


def test_generated_svg_checksum_cannot_be_swapped():
    row = ROWS[2]
    ctx, generated = prepared(row["context"])
    bad = [{**generated[0], "sha256": "wrong"}]
    with pytest.raises(UnsupportedCondition):
        chart(ctx, model(row), bad)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_answers_and_solutions_are_not_math_inputs(row):
    ctx = deepcopy(row["context"])
    for s in ctx["normalized_content"]["sections"]:
        if s["key"] in ("answer", "solution"):
            s["html"] = "<p>wrong</p>"
    assert plan(row, ctx).answer == plan(row).answer
