"""Exact exponential root domains, isolated zeros and the parent's excluded gap."""

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
from solution_runner.pipelines.equations.exponential_radical_product import analyze
from solution_runner.pipelines.equations.exponential_radical_product_figures import (
    SOURCES,
    compatible,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = [
    r
    for r in json.loads(
        Path(__file__)
        .with_name("fixtures")
        .joinpath("exponential_radical_sources.json")
        .read_text()
    )
    if r["group"] == "507795"
]
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {
    "507795": (3, 2, X**2 - 10 * X + 9, X / 3 - 1, 0, 4),
    "507801": (2, 4, X**2 - 10 * X + 16, X / 4 - 1, 2, 6),
    "511495": (2, 3, X**2 - 6 * X + 8, sp.sqrt(2) * X / 4 - 1, 2, 4),
}


def handler():
    return get_handler(get_group_profile("507795").content_rule_key)


def plan(row, context=None, parent=PARENT):
    ctx = _with_required_assets(
        row["context"] if context is None else context, handler().key
    )
    generated = tuple(
        {
            **s,
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in handler().diagram_specs(ctx)
    )
    return handler().plan(
        PlanInput(ctx, parent_solution_html=parent, generated_solution_assets=generated)
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_originals_independent_domain_sign_oracle_and_exact_answer(row):
    a = analyze(read_formula(row["context"])[1])
    base, shift, Q, C, lo, hi = MANUAL[row["task"]]
    assert (a.base, a.exponent, a.radicand, a.coefficient) == (base, X / 2, Q, C)
    positive = sp.Interval.open(0, sp.oo)
    domain = sp.solve_univariate_inequality(Q >= 0, X, relational=False).intersect(
        positive
    )
    oracle = domain.intersect(
        sp.solve_univariate_inequality(C >= 0, X, relational=False).union(
            sp.FiniteSet(*sp.solve(Q, X))
        )
    )
    same_set(a.positive_domain, domain)
    same_set(a.positive_solution, oracle)
    expected = sp.Union(sp.FiniteSet(lo), sp.Interval(hi, sp.oo))
    same_set(a.solution, expected)
    same_set(answer_set(plan(row).answer), expected)
    assert a.coefficient_zero == shift and not a.domain.contains(shift)
    assert a.solution.contains(lo) and a.solution.contains(hi)
    assert a.points == (lo, hi) and a.signs == (-1, 1)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_unsquared_original_product_on_domain_and_at_both_root_zeros(row):
    a = analyze(read_formula(row["context"])[1])
    base, shift, Q, _C, lo, hi = MANUAL[row["task"]]
    for point in set(map(sp.Integer, range(-2, 9))) | {sp.Rational(lo + hi, 2)}:
        t = sp.Integer(base) ** (point / 2)
        q = sp.simplify(Q.subs(X, t))
        c = sp.Integer(base) ** ((point - shift) / 2) - 1
        if q < 0:
            assert not a.domain.contains(point) and not a.solution.contains(point)
        else:
            assert bool(a.solution.contains(point)) == bool(
                sp.simplify(c * sp.sqrt(q)) >= 0
            )
    assert not a.domain.contains(a.coefficient_zero)


def test_odd_shift_retains_exact_quadratic_coefficient_and_threshold():
    a = analyze(read_formula(ROWS[-1]["context"])[1])
    assert a.coefficient == sp.sqrt(2) * X / 4 - 1 and a.coefficient_stage.zeros == (
        2 * sp.sqrt(2),
    )
    assert a.coefficient_zero == 3
    assert sp.simplify(a.coefficient.subs(X, sp.Integer(2) ** sp.Rational(3, 2))) == 0


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_domain_then_zeros_then_signs_readonly_and_idempotent(row):
    ctx = deepcopy(row["context"])
    before = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == before and p.solution_html.count("<img ") == 1
    assert (
        p.solution_html.index("область определения")
        < p.solution_html.index("Найдём нули")
        < p.solution_html.index("не принадлежит области определения")
        < p.solution_html.index("Расставим точки")
        < p.solution_html.index("<img ")
        < p.solution_html.index("решение исходного")
    )
    assert "открытый промежуток исключён" in p.solution_html
    assert all(
        t["transformation_target_id"].startswith(
            (
                "section:answer",
                "section:solution",
                "asset:exponential_root_product_domain",
            )
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
    assert (
        record["status"] == "prepared"
        and record["transformations"] == list(p.transformations)
        and gateway.reads == [ctx["problem_id"]]
    )
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


@pytest.mark.parametrize("row", ROWS[:2], ids=lambda r: r["task"])
def test_native_chart_reused_exactly_and_restored_when_missing(row):
    uid = row["context"]["normalized_content"]["assets"][0]["asset_id"]
    a = analyze(read_formula(row["context"])[1])
    assert compatible(SOURCES["figures"][uid], a)
    assert uid in plan(row).solution_html and not handler().diagram_specs(
        row["context"]
    )
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = []
    restored = _with_required_assets(ctx, handler().key)
    assert (
        restored["normalized_content"]["assets"][0]["asset_id"] == uid
        and uid in plan(row, ctx).solution_html
    )


def test_generated_chart_marks_only_domain_zeros_and_excludes_open_middle():
    specs = handler().diagram_specs(ROWS[-1]["context"])
    assert len(specs) == 1
    root = ET.fromstring(specs[0]["svg_text"])
    assert root.attrib["viewBox"] == "0 0 179.1206 39.7533"
    circles = root.findall(".//{*}circle")
    assert [c.attrib["data-point"] for c in circles] == ["2", "4"]
    assert all(
        c.attrib["data-closed"] == "true" and c.attrib["r"] == "2.6929" for c in circles
    )
    signs = [e for e in root.iter() if "data-sign" in e.attrib]
    assert [e.attrib["data-sign"] for e in signs] == ["-1", "1"]
    assert all(e.attrib["fill"] == "#143B8F" for e in signs)
    gap = next(e for e in root.iter() if "data-excluded-domain-gap" in e.attrib)
    assert (
        gap.attrib["data-excluded-domain-gap"] == "open"
        and gap.attrib["stroke"] == "#143B8F"
    )
    assert not any(e.tag.endswith("rect") for e in root.iter())
    labels = [e.text for e in root.findall(".//{*}text")]
    assert "2" in labels and "4" in labels and "3" not in labels


def test_native_chart_ignores_an_unplotted_zero_only_while_it_stays_inside_gap():
    ctx = deepcopy(ROWS[0]["context"])
    soup = BeautifulSoup(
        next(
            s["html"]
            for s in ctx["normalized_content"]["sections"]
            if s["key"] == "condition"
        ),
        "html.parser",
    )
    formula = soup.select_one("[data-inline-latex]")
    formula["data-inline-latex"] = formula["data-inline-latex"].replace("x-2", "x-3")
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition")[
        "html"
    ] = str(soup)
    a = analyze(read_formula(ctx)[1])
    assert a.coefficient_zero == 3 and compatible(
        next(iter(SOURCES["figures"].values())), a
    )
    assert not handler().diagram_specs(ctx)


def test_decreasing_coordinate_reverses_domain_rays_and_outer_signs():
    formula = (
        read_formula(ROWS[0]["context"])[1]
        .replace("x-2", "-x-2")
        .replace("3^{x}", "3^{-x}")
    )
    a = analyze(formula)
    same_set(a.solution, sp.Union(sp.Interval(-sp.oo, -4), sp.FiniteSet(0)))
    assert a.points == (-4, 0) and a.signs == (1, -1)
    assert not compatible(next(iter(SOURCES["figures"].values())), a)


@pytest.mark.parametrize(
    "formula",
    [
        r"(3^{\frac{x-2}{2}}-1)\sqrt{3^x-10\sqrt{3^x}+9}\le0",
        r"(3^{\frac{x-2}{2}}-1)\sqrt{3^x-10\sqrt{3^x}+9}\ge1",
        r"(3^{\frac{x-2}{2}}-1)\sqrt{3^x-10\sqrt{3^x}+9}+1\ge0",
        r"(3^{\frac{x-2}{2}}-1)\sqrt{3^x-10\sqrt{3^x}+9}\sqrt{3^x-1}\ge0",
        r"(3^{\frac{x-5}{2}}-1)\sqrt{3^x-10\sqrt{3^x}+9}\ge0",
        r"(3^{\frac{x-2}{2}}-1)\sqrt{3^x+1}\ge0",
        r"(3^{\frac{x-2}{2}}-1)\sqrt{5^x-10\sqrt{3^x}+9}\ge0",
        r"(x-1)\sqrt{3^x-10\sqrt{3^x}+9}\ge0",
        r"(3^{\frac{x-2}{2}}-1)\sqrt{3^x-10\sqrt{3^x}+9+\frac{x-1}{x-1}-1}\ge0",
        r"(3^{\frac{x^2-2}{2}}-1)\sqrt{3^{x^2}-10\sqrt{3^{x^2}}+9}\ge0",
    ],
)
def test_complete_ast_parent_shape_and_original_domain_guards(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_unknown_parent_and_unreviewed_asset_are_rejected():
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], parent=PARENT + " ")
    ctx = deepcopy(ROWS[0]["context"])
    ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)


def test_saved_answer_ignored_and_extra_condition_instruction_rejected():
    ctx = deepcopy(ROWS[0]["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    assert plan(ROWS[0], ctx).answer == plan(ROWS[0]).answer
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition")[
        "html"
    ] += "<p>Дополнительно x&gt;0</p>"
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)
