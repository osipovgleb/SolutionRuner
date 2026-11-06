"""Exact common-base comparison, native proofs and read-only preparation."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_exam_trigonometric import replay
from test_rational_inequality import answer_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.dashboard.teacherhelper import teacherhelper_navigation
from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exponential_inequality_common_base import (
    common_base,
    compare,
)
from solution_runner.pipelines.equations.exponential_inequality_groups import GROUPS
from solution_runner.pipelines.equations.exponential_inequality_parser import (
    ExponentialParser,
)
from solution_runner.pipelines.equations.rational_inequality import analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

SOURCES = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("exponential_inequality_sources.json")
    .read_text()
)
RULE = "exam-exponential-inequality-common-base"


def parent(row):
    return next(
        s["html"]
        for r in SOURCES
        if r["task"] == row["group"]
        for s in r["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def plan(row, ctx):
    return get_handler(RULE).plan(PlanInput(ctx, parent_solution_html=parent(row)))


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_native_answers_and_symbolic_logarithmic_oracle(row):
    a = compare(read_formula(row["context"])[1])
    left, right = (c * b**g for c, b, g in a.powers)
    assert left.is_positive is True and right.is_positive is True and a.base > 1
    assert sp.simplify(a.left.value - a.right.value - (left - right)) == 0
    log_difference = sp.expand_log(sp.log(left), force=True) - sp.expand_log(
        sp.log(right), force=True
    )
    oracle = sp.simplify(log_difference / sp.expand_log(sp.log(a.base)))
    assert sp.expand(oracle - a.stage.original) == 0
    relation = {"<=": sp.Le, ">=": sp.Ge, "<": sp.Lt, ">": sp.Gt}[a.operator]
    independent = sp.solve_univariate_inequality(
        relation(oracle, 0), X, relational=False
    )
    assert independent == a.stage.solution == answer_set(row["expected_answer"])
    assert answer_set(plan(row, row["context"]).answer) == independent


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_every_common_base_identity_and_inequality_preserves_the_computed_set(row):
    p = plan(row, row["context"])
    a = compare(read_formula(row["context"])[1])
    checked = 0
    for span in BeautifulSoup(p.solution_html, "html.parser").find_all(
        "span", attrs={"data-inline-latex": True}
    ):
        formula = span["data-inline-latex"]
        if "=" in formula and "x" not in formula:
            for identity in formula.split(r",\quad "):
                left, right = identity.split("=")
                assert (
                    sp.simplify(
                        ExponentialParser(left).parse().value
                        - ExponentialParser(right).parse().value
                    )
                    == 0
                )
        if "x" not in formula or not re.search(
            r"\\(?:le|ge|gt|lt)(?![a-zA-Z])|<|>", formula
        ):
            continue
        try:
            solution = compare(formula).stage.solution
        except UnsupportedCondition:
            solution = analyze(formula).solution
        assert solution == a.stage.solution, formula
        checked += 1
    assert checked >= 4
    assert "показательная функция возрастает" in p.solution_html


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_plan_replay_and_gateway_never_request_writes_or_assets(row):
    ctx = deepcopy(row["context"])
    p = plan(row, ctx)
    assert ctx == row["context"]
    assert not get_handler(RULE).diagram_specs(ctx) and not get_handler(
        RULE
    ).asset_requirements(ctx)
    assert all(
        not t["transformation_target_id"].startswith(("asset:", "section:condition"))
        for t in p.transformations
    )
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        RULE,
        parent_solution_html=parent(row),
    )
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == p.answer and record["transformations"] == list(
        p.transformations
    )
    assert (
        gateway.ctx == ctx
        and len(gateway.reads) == 1
        and not record.get("generated_diagrams")
    )
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


@pytest.mark.parametrize(
    "record", [r for r in GROUPS if r[-1] == RULE], ids=lambda r: r[0]
)
def test_exact_catalog_registration_uses_one_shared_rule(record):
    key, group_id, index, theme, theme_index, theme_id, rule = record
    p = get_group_profile(key)
    assert rule == RULE and p.content_rule_key == RULE
    assert (
        p.source_group_id,
        p.group_order_index,
        p.theme_title,
        p.theme_order_index,
        p.snapshot_theme_id,
        p.category_key,
    ) == (group_id, index, theme, theme_index, theme_id, "16")
    nav = teacherhelper_navigation(p)
    assert (
        nav["category_id"] == "f1f2f85a-56b3-4188-b1d7-d330025173a7"
        and nav["group_id"] == group_id
        and nav["theme_id"] == theme_id
    )


@pytest.mark.parametrize(
    "bases,expected",
    [
        ((25, sp.Rational(1, 5)), 5),
        ((64, sp.Rational(1, 8)), 8),
        ((16, sp.Rational(1, 4)), 4),
        ((sp.Rational(4, 9), sp.Rational(8, 27)), sp.Rational(3, 2)),
    ],
)
def test_prime_vectors_choose_the_greatest_increasing_common_rational_base(
    bases, expected
):
    assert common_base(tuple(map(sp.Rational, bases))) == expected


@pytest.mark.parametrize(
    "formula,expected",
    [
        (
            r"(\frac{1}{4})^{x^2}\le(\frac{1}{2})^x",
            sp.Interval(-sp.oo, 0) | sp.Interval(sp.Rational(1, 2), sp.oo),
        ),
        (r"2^x\le8", sp.Interval(-sp.oo, 3)),
        (r"0{,}5^x\le0{,}25", sp.Interval(2, sp.oo)),
        (r"4^{x^2}<2^{2x}", sp.Interval.open(0, 1)),
    ],
)
def test_reciprocal_bases_constants_and_strictness_keep_the_correct_orientation(
    formula, expected
):
    assert compare(formula).stage.solution == expected


@pytest.mark.parametrize(
    "formula",
    [
        r"2^x+3^x\le4",
        r"2^{3^x}\le4",
        r"(-2)^x\le4",
        r"x^x\le4",
        r"2^{x^3}\le4",
        r"2^{\frac{x}{x-1}}\le8",
        r"2^x\le3^x",
        r"2^x\le3",
        r"2^x\le4\text{и }x>0",
        r"__import__(x)\le0",
    ],
)
def test_unreviewed_domains_bases_and_unbounded_powers_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        compare(formula)


@pytest.mark.parametrize(
    "change", ["answer", "solution", "extra_instruction", "asset", "parent"]
)
def test_only_the_condition_computes_the_answer_and_unknown_inputs_are_rejected(change):
    row = SOURCES[0]
    ctx = deepcopy(row["context"])
    if change in ("answer", "solution"):
        next(s for s in ctx["normalized_content"]["sections"] if s["key"] == change)[
            "html"
        ] = "<p>Неверно</p>"
        assert answer_set(plan(row, ctx).answer) == answer_set(row["expected_answer"])
        return
    if change == "extra_instruction":
        next(
            s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
        )["html"] += "<p>Укажите только целые решения.</p>"
    elif change == "asset":
        ctx["normalized_content"]["assets"] = [
            {"asset_id": "unreviewed", "asset_key": "image_1"}
        ]
    with pytest.raises(UnsupportedCondition):
        if change == "parent":
            get_handler(RULE).plan(
                PlanInput(ctx, parent_solution_html=parent(row) + " ")
            )
        else:
            plan(row, ctx)
