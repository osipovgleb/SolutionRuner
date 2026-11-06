"""Common typed substitutions, original domains, isolated roots and exact charts."""

import hashlib
import json
import re
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
    _prepared_record,
    _with_required_assets,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.rational_exponential_figures import SOURCES
from solution_runner.pipelines.equations.rational_exponential_proof import (
    common_fraction,
    parts,
)
from solution_runner.pipelines.equations.rational_exponential_substitution import (
    analyze,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import (
    RationalParser,
    X,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("rational_exponential_inequality_sources.json")
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


def rule(row):
    return get_group_profile(row["group"]).content_rule_key


def plan(row, ctx=None, parent=None):
    context = _with_required_assets(ctx or row["context"], rule(row))
    return get_handler(rule(row)).plan(
        PlanInput(context, parent_solution_html=parent or PARENTS[row["group"]])
    )


def model(row):
    return analyze(read_formula(row["context"])[1])


def zero(value):
    assert sp.simplify(sp.cancel(sp.expand(value.rewrite(sp.exp)))) == 0


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_native_exact_rational_substitution_source_answers_and_independent_cas(row):
    a = model(row)
    t = a.base**a.exponent
    zero(a.original - a.stage.original.subs(X, t))
    relation = {"<=": sp.Le, ">=": sp.Ge, "<": sp.Lt, ">": sp.Gt}[a.operator]
    expected = sp.solve_univariate_inequality(
        relation(a.stage.original, 0), X, relational=False
    ) - sp.FiniteSet(*a.stage.holes)
    same_set(expected, a.stage.solution)
    same_set(
        a.solution,
        answer_set(row["expected_answer"].replace(r"\left", "").replace(r"\right", "")),
    )
    same_set(answer_set(plan(row).answer), a.solution)
    for level, log_level, roots in a.back:
        assert len(roots) == 1
        zero(a.base**log_level - level)
        zero(a.exponent.subs(X, roots[0]) - log_level)
    n, d = common_fraction(a.stage)
    zero(n / d - a.stage.original)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_source_immutability_readonly_gateway_replay_and_exact_asset_reuse(row):
    ctx = deepcopy(row["context"])
    p = plan(row, ctx)
    h = get_handler(rule(row))
    assert ctx == row["context"] and not h.diagram_specs(ctx)
    assert all(
        t["transformation_target_id"].startswith(("section:answer", "section:solution"))
        for t in p.transformations
    )
    images = ctx["normalized_content"]["assets"]
    assert p.solution_html.count("<img ") == len(images)
    for asset in images:
        assert asset["asset_id"] in p.solution_html
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        rule(row),
        parent_solution_html=PARENTS[row["group"]],
    )
    assert record["status"] == "prepared", record
    assert (
        record["transformations"] == list(p.transformations)
        and record["expected_answer"] == p.answer
    )
    assert gateway.reads == [ctx["problem_id"]] and gateway.ctx == ctx
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations
    assert ctx["normalized_content"]["assets"] == images


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_every_displayed_substitution_inequality_is_sign_equivalent(row):
    a = model(row)
    parent = PARENTS[row["group"]]
    frame = SOURCES["parents"][hashlib.sha256(parent.encode()).hexdigest()]
    variable = frame["variable"]
    count = 0
    relation = re.compile(r"(\\(?:ge|le)(?![a-zA-Z])|<|>)")
    for span in BeautifulSoup(plan(row).solution_html, "html.parser").find_all(
        attrs={"data-inline-latex": True}
    ):
        text = span["data-inline-latex"]
        assert r"\mathtt" not in text
        if (
            variable not in text
            or not text.endswith("0")
            or text.count("=")
            or r"\quad" in text
            or r"\begin" in text
        ):
            continue
        values = relation.split(text)
        if len(values) != 3:
            continue
        left, op, right = values
        if right != "0":
            continue
        source = re.sub(r"(?<![A-Za-z])" + variable + r"(?![A-Za-z])", "x", left)
        try:
            value = RationalParser(source).parse().value
        except UnsupportedCondition:
            continue
        if not value.free_symbols:
            continue
        if (
            op == ">"
            and value.is_polynomial(X)
            and sp.solve_univariate_inequality(value > 0, X, relational=False)
            == sp.S.Reals
        ):
            continue
        ratio = sp.cancel(value / a.stage.original)
        assert ratio.is_Rational and ratio != 0, (row["task"], text, ratio)
        canonical = {r"\ge": ">=", r"\le": "<=", "<": "<", ">": ">"}[op]
        expected = (
            a.operator
            if ratio > 0
            else {">=": "<=", "<=": ">=", ">": "<", "<": ">"}[a.operator]
        )
        assert canonical == expected, (row["task"], text)
        count += 1
    assert count >= 2


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_rendered_parent_variable_and_no_duplicate_exponential_identities(row):
    html = plan(row).solution_html
    variable = SOURCES["parents"][
        hashlib.sha256(PARENTS[row["group"]].encode()).hexdigest()
    ]["variable"]
    formulas = [
        s["data-inline-latex"]
        for s in BeautifulSoup(html, "html.parser").find_all(
            attrs={"data-inline-latex": True}
        )
    ]
    assert any(s.startswith(variable + "=") and s.endswith(">0") for s in formulas)
    identities = [
        s
        for s in formulas
        if "=" in s and not any(token in s for token in (r"\iff", r"\ne", r"\quad"))
    ]
    assert len(identities) == len(set(identities))
    assert r"\gex" not in html and r"\lex" not in html


@pytest.mark.parametrize(
    "key",
    [
        "513101",
        "517565",
        "682460",
        "682469",
        "509949",
        "509970",
        "517461",
        "517468",
        "532283",
        "660809",
    ],
)
def test_repeated_zero_survives_as_a_real_isolated_solution(key):
    row = next(r for r in ROWS if r["task"] == key)
    a = model(row)
    assert any(isinstance(p, sp.FiniteSet) for p in parts(a.positive_solution))
    assert "отдельные решения" in plan(row).solution_html


def test_exponential_denominator_cancellation_retains_original_hole():
    a = analyze(r"\frac{2^x-2}{2^x-2}\ge 0")
    assert a.stage.holes == (2,) and a.solution == sp.S.Reals - sp.FiniteSet(1)


def test_cancellation_inside_exponent_retains_extra_original_x_pole():
    a = analyze(r"\frac{1}{2^{x+\frac{x-3}{x-3}}-4}>0")
    assert a.extra_poles == (3,)
    assert a.solution == sp.Interval.open(1, sp.oo) - sp.FiniteSet(3)


def test_decreasing_substitution_changes_endpoint_order_and_sign():
    row = next(r for r in ROWS if r["task"] == "508497")
    a = model(row)
    assert a.exponent == -X and a.solution.contains(-2) and not a.solution.contains(-1)
    assert "-\\log_{2}" in a.answer
    assert "отрицательный коэффициент" in plan(row).solution_html


@pytest.mark.parametrize(
    "formula",
    [
        r"x+2^x\ge 0",
        r"2^{x^2}\ge 1",
        r"2^{x/(x+1)}\ge 1",
        r"\frac{1}{2^x+x}\ge 0",
        r"\frac{1}{2^x-2^x}\ge 0",
        r"2^x+3^x\ge 0",
        r"1\ge 0",
        r"unknown(x)\ge 0",
    ],
)
def test_unsupported_or_undefined_full_inputs_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


@pytest.mark.parametrize(
    "field,value",
    [
        ("asset_id", "foreign"),
        ("asset_key", "wrong"),
        ("kind", "wrong"),
        ("url", "/assets/other"),
    ],
)
def test_unknown_or_relabelled_source_chart_is_rejected(field, value):
    row = next(r for r in ROWS if r["task"] == "532283")
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"][0][field] = value
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


def test_wrong_zero_multiplicity_cannot_reuse_the_same_chart(monkeypatch):
    row = next(r for r in ROWS if r["task"] == "532283")
    key = row["context"]["normalized_content"]["assets"][0]["asset_id"]
    monkeypatch.setitem(SOURCES["figures"][key]["multiplicities"]["zeros"], "2", 4)
    with pytest.raises(UnsupportedCondition):
        plan(row)


def test_compatible_missing_chart_reuses_existing_id_and_rejects_duplicates():
    row = next(r for r in ROWS if r["task"] == "532283")
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = []
    for section in ctx["normalized_content"]["sections"]:
        section["asset_keys"] = []
    assert (
        row["context"]["normalized_content"]["assets"][0]["asset_id"]
        in plan(row, ctx).solution_html
    )
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] *= 2
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


def test_unknown_parent_and_unreviewed_image_in_plain_frame_rejected():
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], parent=PARENTS[ROWS[0]["group"]] + "wrong")
    ctx = deepcopy(ROWS[0]["context"])
    ctx["normalized_content"]["assets"] = [
        deepcopy(
            next(r for r in ROWS if r["task"] == "532283")["context"][
                "normalized_content"
            ]["assets"][0]
        )
    ]
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_source_answers_and_solutions_are_not_calculation_inputs(row):
    ctx = deepcopy(row["context"])
    for s in ctx["normalized_content"]["sections"]:
        if s["key"] in ("solution", "answer"):
            s["html"] = "<p>wrong</p>"
    assert plan(row, ctx).answer == plan(row).answer
