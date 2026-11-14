"""Complete parent sign cases, original rational-base poles and reviewed asset roles."""

import json
import math
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from test_exam_trigonometric import replay
from test_exponential_inequality_preimages import answer_set
from test_exponential_inequality_quadratic import same_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.logarithm_sign_cases import (
    base_order,
    product_cases,
)
from solution_runner.pipelines.equations.logarithm_sign_cases_proof import render_order
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_sign_cases_sources.json")
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
PRODUCTS = {
    "508547": (4 - X, X + 4, X + 5, 6 - X),
    "508550": (11 - X, X + 7, X + 5, 9 - X),
    "508551": (2 - X, X + 2, X + 3, 3 - X),
    "511253": (2 * X, X + 4, X, 2 - X),
    "513274": (2 - X, X + 2, X + 3, 3 - X),
}
ORDERS = {
    "509587": (X / (X - 1), X / 2, sp.Integer(5)),
    "509608": (X / (X - 3), X / 3, sp.Integer(7)),
    "511267": (X + 1, 3 - X, sp.Integer(2)),
}


def handler(row):
    return get_handler(get_group_profile(row["group"]).content_rule_key)


def plan(row, ctx=None, parent=None):
    return handler(row).plan(
        PlanInput(
            row["context"] if ctx is None else ctx,
            parent_solution_html=PARENTS[row["group"]] if parent is None else parent,
        )
    )


def model(row):
    return (product_cases if row["task"] in PRODUCTS else base_order)(
        read_formula(row["context"])[1]
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_manual_arguments_answers_full_domains_and_independent_cas(row):
    a = model(row)
    same_set(a.solution, answer_set(row["expected_answer"]))
    assert plan(row).answer == a.answer
    if row["task"] in PRODUCTS:
        G, A, H, B = PRODUCTS[row["task"]]
        assert [(v.base, v.argument) for v in a.atoms] == [(G, A), (H, B)]
        values = (G, A, H, B)
        sign = (G - 1) * (A - 1) * (H - 1) * (B - 1)
    else:
        G, H, C = ORDERS[row["task"]]
        assert [(v.base, v.argument) for v in a.atoms] == [(G, C), (H, C)]
        values = (G, H)
        sign = sp.cancel((H - G) / ((G - 1) * (H - 1)))
    domain = (
        sp.Intersection(
            *(
                sp.solve_univariate_inequality(v > 0, X, relational=False)
                for v in values
            )
        )
        - sp.solveset(G - 1, X, domain=sp.S.Reals)
        - sp.solveset(H - 1, X, domain=sp.S.Reals)
    )
    same_set(a.domain, domain)
    oracle = sp.solve_univariate_inequality(sign <= 0, X, relational=False).intersect(
        domain
    )
    same_set(a.solution, oracle)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_logarithm_values_and_unit_or_nonpositive_bases(row):
    a = model(row)
    for p in (sp.Rational(i, 10) for i in range(-70, 111)):
        vals = [atom.base.subs(X, p) for atom in a.atoms] + [
            atom.argument.subs(X, p) for atom in a.atoms
        ]
        if not all(v.is_finite for v in vals):
            assert a.solution.contains(p) is sp.false
            continue
        G, H, A, B = map(float, vals)
        valid = min(G, H, A, B) > 0 and G != 1 and H != 1
        value = (
            (
                math.log(A, G) * math.log(B, H)
                if row["task"] in PRODUCTS
                else math.log(A, G) - math.log(B, H)
            )
            if valid
            else 0
        )
        assert bool(a.solution.contains(p)) == (valid and value <= 1e-8), (
            row["task"],
            p,
        )
    for hole in a.poles:
        assert (
            a.domain.contains(hole) is sp.false
            and a.solution.contains(hole) is sp.false
        )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_runtime_replays_with_condition_and_assets_untouched(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == original and not handler(row).diagram_specs(ctx)
    assert all(
        t["transformation_target_id"].startswith(("section:answer", "section:solution"))
        for t in p.transformations
    )
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        handler(row).key,
        parent_solution_html=PARENTS[row["group"]],
    )
    assert (
        gateway.reads == [ctx["problem_id"]]
        and record["status"] == "prepared"
        and record["transformations"] == list(p.transformations)
    )
    replay(ctx, p.transformations)
    assert (
        ctx["normalized_content"]["assets"] == original["normalized_content"]["assets"]
        and not plan(row, ctx).transformations
    )


@pytest.mark.parametrize(
    "task,index,sign",
    [
        ("508547", 1, 1),
        ("508550", 0, 1),
        ("508551", 1, 1),
        ("511253", 1, -1),
        ("513274", 1, 1),
    ],
)
def test_fixed_factor_index_sign_and_two_parent_base_cases(task, index, sign):
    row = next(r for r in ROWS if r["task"] == task)
    a = model(row)
    assert (
        a.fixed_index == index
        and a.fixed_sign == sign
        and [c.increasing for c in a.cases] == [True, False]
    )
    assert sp.Union(*(s.domain for s in a.sign_regions)) == a.domain
    html = plan(row).solution_html
    assert html.index("Первый случай") < html.index("Второй случай")
    if sign < 0:
        assert a.target == ">=" and a.cases[1].solution == sp.EmptySet
        assert (
            a.solution.contains(sp.Rational(3, 4)) is sp.true
            and a.solution.contains(sp.Rational(1, 4)) is sp.false
        )
        assert "неотрицательный" in html


def test_base_order_retains_negative_left_branch_and_excludes_positive_left_negative_right():
    row = next(r for r in ROWS if r["task"] == "511267")
    a = model(row)
    assert (
        a.solution.contains(-sp.Rational(1, 2)) is sp.true
        and a.solution.contains(sp.Rational(5, 2)) is sp.false
    )
    assert (
        len(a.cases) == 3
        and a.cases[1].solution == sp.Interval.open(-1, 0)
        and a.cases[2].solution == sp.EmptySet
    )
    html = plan(row).solution_html
    assert "Левая часть отрицательна" in html and "Примечание" in html


@pytest.mark.parametrize("task", ["509587", "509608"])
def test_positive_base_parent_cancels_common_positive_x(task):
    row = next(r for r in ROWS if r["task"] == task)
    html = plan(row).solution_html
    assert (
        "первое основание больше единицы" in html
        and "Сократим общий положительный множитель" in html
        and "Примечание" in html
    )


def test_original_cancelled_argument_pole_is_not_lost_at_a_valid_zero():
    row = next(r for r in ROWS if r["task"] == "508547")
    formula = read_formula(row["context"])[1]
    a = product_cases(formula.replace("x+4", r"\frac{x+3}{x+3}(x+4)", 1))
    baseline = model(row)
    same_set(a.solution, baseline.solution - sp.FiniteSet(-3))
    assert -3 in a.poles and a.domain.contains(-3) is sp.false


def test_original_cancelled_rational_base_pole_remains_excluded_at_equality():
    row = next(r for r in ROWS if r["task"] == "509587")
    formula = read_formula(row["context"])[1]
    assert r"\frac{x}{x-1}" in formula
    a = base_order(
        formula.replace(r"\frac{x}{x-1}", r"\frac{x-3}{x-3}\cdot\frac{x}{x-1}", 1)
    )
    same_set(a.solution, sp.Interval.open(2, 3))
    assert 3 in a.poles


def test_two_bases_below_one_use_the_same_reverse_base_order():
    a = base_order(r"\log_{x}2\le\log_{(2x)}2")
    assert any(not c.left_increasing and not c.right_increasing for c in a.cases)
    for p in (sp.Rational(1, 4), sp.Rational(3, 4), sp.Rational(3, 2)):
        expected = math.log(2, float(p)) <= math.log(2, float(2 * p))
        assert bool(a.solution.contains(p)) == expected


def test_every_right_base_below_one_has_no_positive_left_solution():
    a = base_order(r"\log_{\frac{x}{x-1}}5\le\log_{\frac{1}{2x}}5")
    assert a.solution == sp.EmptySet and "несовместны" in render_order(a)


def test_reviewed_alternative_child_figure_is_not_copied_into_the_parent_cases():
    row = next(r for r in ROWS if r["task"] == "513274")
    p = plan(row)
    assert (
        len(row["context"]["normalized_content"]["assets"]) == 1
        and "<img" not in p.solution_html
    )
    assert all(
        not t["transformation_target_id"].startswith("asset:")
        for t in p.transformations
    )
    for kind in ("unknown", "condition", "changed_signature"):
        ctx = deepcopy(row["context"])
        if kind == "unknown":
            ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
        elif kind == "condition":
            next(
                s
                for s in ctx["normalized_content"]["sections"]
                if s["key"] == "condition"
            )["asset_keys"] = ["image_1"]
        else:
            for s in ctx["normalized_content"]["sections"]:
                if s["key"] == "condition":
                    s["html"] = s["html"].replace("3-x", "6-x")
        with pytest.raises(UnsupportedCondition):
            plan(row, ctx)


@pytest.mark.parametrize("group", ["508547", "509587"])
def test_saved_answer_parent_and_unreviewed_assets_are_independent_guards(group):
    row = next(r for r in ROWS if r["group"] == group and r["task"] != group)
    ctx = deepcopy(row["context"])
    for s in ctx["normalized_content"]["sections"]:
        if s["key"] == "answer":
            s["html"] = "<p>999</p>"
    assert plan(row, ctx).answer == model(row).answer
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Чужой родитель.</p>")
    ctx["normalized_content"]["assets"] = [
        {"asset_id": "unknown", "asset_key": "image_1"}
    ]
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_x(x+2)\cdot\log_{x+3}x\le0",
        r"\log_{x^2}(x+2)\cdot\log_{x+3}(3-x)\le0",
        r"\log_{2-x}(x+2)+\log_{x+3}(3-x)\le0",
        r"\log_{2-x}(x+2)\cdot\log_{x+3}(3-x)\ge0",
        r"\log_{2-x}(x+2)\cdot\log_{x+3}(3-x)\le x",
        r"\log_{2-x}(x+2)\cdot\log_{x+3}(3-x)\cdot\log_x2\le0",
    ],
)
def test_unreviewed_product_shapes_and_nonconstant_signs_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        product_cases(formula)


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_{x+1}2\le\log_{3-x}3",
        r"\log_{x+1}1\le\log_{3-x}1",
        r"\log_{x+1}\frac{1}{2}\le\log_{3-x}\frac{1}{2}",
        r"\log_{x^2+1}2\le\log_{3-x}2",
        r"\log_{x+1}2\ge\log_{3-x}2",
        r"\log_{x+1}2+1\le\log_{3-x}2",
    ],
)
def test_unreviewed_arguments_bases_and_outer_comparisons_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        base_order(formula)
