"""Exact positive-domain substitution, native parent methods and read-only plans."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_exam_trigonometric import replay
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.dashboard.teacherhelper import teacherhelper_navigation
from solution_runner.pipelines.core.content_runtime import _prepared_record
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.exponential_inequality_common_base import (
    read_terms,
)
from solution_runner.pipelines.equations.exponential_inequality_groups import GROUPS
from solution_runner.pipelines.equations.exponential_inequality_quadratic import (
    analyze_quadratic,
)
from solution_runner.pipelines.equations.exponential_inequality_quadratic_proof import (
    validate_method,
)
from solution_runner.pipelines.equations.logarithm_arithmetic import actual
from solution_runner.pipelines.equations.logarithm_parser import LogarithmParser
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

SOURCES = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("exponential_inequality_quadratic_sources.json")
    .read_text()
)


def endpoint(text):
    if "infty" in text:
        return -sp.oo if text.startswith("-") else sp.oo
    return actual(LogarithmParser(text).parse().value)


def answer_set(text):
    parts = []
    for item in text.strip().removesuffix(".").strip().split(r"\cup"):
        item = item.strip()
        left, right = map(endpoint, item[1:-1].split(";"))
        parts.append(
            sp.Interval(
                left, right, left_open=item[0] == "(", right_open=item[-1] == ")"
            )
        )
    return sp.Union(*parts)


def same_set(left, right):
    lparts = left.args if isinstance(left, sp.Union) else (left,)
    rparts = right.args if isinstance(right, sp.Union) else (right,)

    def same(l, r):
        if l == r:
            return True
        return (
            isinstance(l, sp.Interval)
            and isinstance(r, sp.Interval)
            and (l.left_open, l.right_open) == (r.left_open, r.right_open)
            and all(
                a == b or sp.simplify(sp.expand_log(a - b, force=True)) == 0
                for a, b in ((l.start, r.start), (l.end, r.end))
            )
        )

    assert len(lparts) == len(rparts) and all(
        any(same(l, r) for r in rparts) for l in lparts
    )


def parent(row):
    source = next(v for v in SOURCES if v["task"] == row["group"])
    return next(
        s["html"]
        for s in source["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def rule(row):
    return get_group_profile(row["group"]).content_rule_key


def plan(row, ctx=None):
    return get_handler(rule(row)).plan(
        PlanInput(ctx or row["context"], parent_solution_html=parent(row))
    )


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_native_source_answers_and_independent_quadratic_oracle(row):
    a = analyze_quadratic(read_formula(row["context"])[1])
    actual_power = a.base**a.exponent
    assert actual_power.is_positive is True
    transformed = sp.expand_power_exp(a.stage.original.subs(X, actual_power))
    original = sp.expand_power_exp(a.original * actual_power**a.multiply_degree)
    assert sp.simplify(sp.expand((original - transformed).rewrite(sp.exp))) == 0
    relation = {"<=": sp.Le, ">=": sp.Ge, "<": sp.Lt, ">": sp.Gt}[a.operator]
    independent = sp.solve_univariate_inequality(
        relation(a.stage.original, 0), X, relational=False
    )
    assert a.positive_solution == independent.intersect(sp.Interval.open(0, sp.oo))
    for t, value, branch in a.back:
        assert sp.simplify(a.base**value - t) == 0
        assert sp.simplify(a.exponent.subs(X, branch[0]) - value) == 0
    same_set(a.solution, answer_set(row["expected_answer"]))
    same_set(answer_set(a.answer), a.solution)
    same_set(answer_set(plan(row).answer), a.solution)


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_readonly_gateway_replay_no_assets_and_condition_immutability(row):
    ctx = deepcopy(row["context"])
    p = plan(row, ctx)
    assert ctx == row["context"]
    handler = get_handler(rule(row))
    assert not handler.diagram_specs(ctx) and not handler.asset_requirements(ctx)
    assert all(
        not t["transformation_target_id"].startswith(("asset:", "section:condition"))
        for t in p.transformations
    )
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        rule(row),
        parent_solution_html=parent(row),
    )
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == p.answer and record["transformations"] == list(
        p.transformations
    )
    assert len(gateway.reads) == 1 and not record.get("generated_diagrams")
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_parent_substitution_order_and_exact_root_styles(row):
    html = plan(row).solution_html
    lines = [
        s["data-inline-latex"]
        for s in BeautifulSoup(html, "html.parser").find_all(
            "span", attrs={"data-inline-latex": True}
        )
    ]
    if row["group"] in ("508296", "508436"):
        assert not any(re.match(r"[ty]=", f) for f in lines)
    elif row["group"] == "508359":
        assert any(f.startswith("y=") and f.endswith(">0") for f in lines)
        assert html.index("Пусть") < html.index("Умножим")
    else:
        assert any(f.startswith("t=") and f.endswith(">0") for f in lines)
        assert html.index("Упростим") < html.index("Пусть")
    if row["task"] == "508368":
        assert r"\log_{2}(\frac{2}{5})" in plan(row).answer
        assert "10g" in row["source_answer"]
    if row["task"] == "511505":
        assert r"\frac{1}{2}" in plan(row).answer
    if row["task"] in ("508296", "508402", "511505"):
        assert any(r"\right)^{2}>0" in f and " - " in f for f in lines)
    if row["task"] == "508437":
        assert "- x" in html and "730" in html
    if row["group"] == "508436":
        assert any(r"\cdot" in f and "^{" in f for f in lines)


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_displayed_polynomials_and_power_inequalities_are_equivalent(row):
    a = analyze_quadratic(read_formula(row["context"])[1])
    checked = 0
    for span in BeautifulSoup(plan(row).solution_html, "html.parser").find_all(
        "span", attrs={"data-inline-latex": True}
    ):
        formula = span["data-inline-latex"]
        if (
            "=" in formula
            or not formula.endswith("0")
            or len(re.findall(r"\\(?:le|ge|gt|lt)(?![a-zA-Z])|<|>", formula)) != 1
        ):
            continue
        explicit = bool(re.search(r"(?<![A-Za-z\\])[ty](?![A-Za-z])", formula))
        surrogate = re.sub(r"(?<![A-Za-z\\])[ty](?![A-Za-z])", "x", formula)
        left, right, _, op = read_terms(surrogate)
        value = left.value - right.value
        # Positivity of the substituted power is a domain statement, not an equivalent inequality.
        if value.is_positive is True:
            assert op == ">"
            continue
        reference = a.stage.original if explicit else a.original
        ratio = sp.simplify(
            sp.cancel(
                sp.expand(value.rewrite(sp.exp)) / sp.expand(reference.rewrite(sp.exp))
            )
        )
        if explicit:
            ratio = ratio.subs(X, sp.Symbol("positive_power", positive=True))
        assert ratio.is_positive is True and op == a.operator, formula
        checked += 1
    assert checked >= 2


@pytest.mark.parametrize(
    "record",
    [r for r in GROUPS if r[-1] != "exam-exponential-inequality-common-base"],
    ids=lambda r: r[0],
)
def test_exact_catalog_registration_and_navigation(record):
    key, group_id, index, theme, theme_index, theme_id, content_rule = record
    p = get_group_profile(key)
    assert (
        p.source_group_id,
        p.group_order_index,
        p.theme_title,
        p.theme_order_index,
        p.snapshot_theme_id,
        p.category_key,
        p.content_rule_key,
    ) == (group_id, index, theme, theme_index, theme_id, "16", content_rule)
    nav = teacherhelper_navigation(p)
    assert (
        nav["category_id"] == "f1f2f85a-56b3-4188-b1d7-d330025173a7"
        and nav["group_id"] == group_id
        and nav["theme_id"] == theme_id
    )


@pytest.mark.parametrize(
    "formula,expected",
    [
        (r"4^x-2\cdot2^x+1\le0", sp.FiniteSet(0)),
        (r"4^x-2\cdot2^x+1<0", sp.EmptySet),
        (r"4^x+2\cdot2^x-3\le0", sp.Interval(-sp.oo, 0)),
        (r"4^x-3\cdot2^x\le0", sp.Interval(-sp.oo, sp.log(3) / sp.log(2))),
        (
            r"9^{-x}-4\cdot3^{-x}+3>0",
            sp.Interval.open(-sp.oo, -1) | sp.Interval.open(0, sp.oo),
        ),
        (r"4^x-5\cdot2^x+6<0", sp.Interval.open(1, sp.log(3) / sp.log(2))),
    ],
)
def test_positive_domain_strictness_tangency_zero_boundary_and_decreasing_inverse(
    formula, expected
):
    same_set(analyze_quadratic(formula).solution, expected)


@pytest.mark.parametrize(
    "formula",
    [
        r"2^{x^2}-3\cdot2^x+2\le0",
        r"\frac{4^x}{x-1}+2^x\le3",
        r"\frac{4^x}{2^x-1}+2^x\le3",
        r"2^x+3^x\le4",
        r"2^{3^x}+2^x\le4",
        r"2^{x^3}+2^x\le4",
        r"x^x+2^x\le4",
        r"(-2)^x+4^x\le4",
        r"2^{\frac{x}{x-1}}+4^x\le4",
        r"8^x+2^x\le4",
        r"2^{x+1000000000000}+4^x\le4",
        r"2^x+4^x\le4\text{и }x>0",
    ],
)
def test_unreviewed_degree_domains_bases_and_instructions_fail_closed(formula):
    with pytest.raises(UnsupportedCondition):
        analyze_quadratic(formula)


@pytest.mark.parametrize(
    "change", ["answer", "solution", "asset", "instruction", "parent", "method"]
)
def test_only_condition_computes_answers_and_parent_method_is_certified(change):
    row = SOURCES[0]
    ctx = deepcopy(row["context"])
    if change in ("answer", "solution"):
        next(s for s in ctx["normalized_content"]["sections"] if s["key"] == change)[
            "html"
        ] = "<p>Неверно</p>"
        assert plan(row, ctx).answer == plan(row).answer
        return
    if change == "asset":
        ctx["normalized_content"]["assets"] = [
            {"asset_id": "unknown", "asset_key": "image_1"}
        ]
    elif change == "instruction":
        next(
            s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
        )["html"] += "<p>Укажите только целые решения.</p>"
    with pytest.raises(UnsupportedCondition):
        if change == "parent":
            get_handler(rule(row)).plan(
                PlanInput(ctx, parent_solution_html=parent(row) + " ")
            )
        elif change == "method":
            validate_method(analyze_quadratic(read_formula(ctx)[1]), "offset_quadratic")
        else:
            plan(row, ctx)
