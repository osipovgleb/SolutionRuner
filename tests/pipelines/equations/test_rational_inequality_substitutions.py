"""Native substitution proofs preserve exact domains, source charts and inverse maps."""

import json
import re
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
from solution_runner.pipelines.equations.rational_inequality_figures import read
from solution_runner.pipelines.equations.rational_inequality_parser import (
    RationalParser,
    X,
)
from solution_runner.pipelines.equations.rational_inequality_substitution_proof import (
    common_fraction,
)
from solution_runner.pipelines.equations.rational_inequality_substitutions import (
    inverse_set,
    model,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition

SOURCES = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("rational_inequality_substitution_sources.json")
    .read_text()
)
METHODS = {"508347": "affine_radical", "508397": "reciprocal_square"}


def handler(row):
    return get_handler(
        "exam-rational-inequality-" + METHODS[row["group"]].replace("_", "-")
    )


def parent(row):
    p = next(r for r in SOURCES if r["task"] == row["group"])
    return next(
        s["html"]
        for s in p["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )


def computed_answer_set(text):
    return answer_set(re.sub(r"(?<=\d)\s*\\left\(", r"\\cdot(", text))


def plan(row, context):
    h = handler(row)
    ctx = _with_required_assets(context, h.key)
    generated = tuple(
        {
            **spec,
            "source_asset_id": "preview-" + spec["sha256"][:16],
            "url": "/assets/preview-" + spec["sha256"][:16],
        }
        for spec in h.diagram_specs(ctx)
    )
    return h.plan(
        PlanInput(
            ctx, parent_solution_html=parent(row), generated_solution_assets=generated
        )
    )


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_source_answers_original_domains_and_exact_inverse_substitution(row):
    a = read(row["context"])[1]
    m = model(a, METHODS[row["group"]])
    assert a.solution == answer_set(row["expected_answer"])
    relation = {"<=": sp.Le, ">=": sp.Ge}[a.operator]
    independent = sp.solve_univariate_inequality(
        relation(a.original, 0), X, relational=False
    ) - sp.FiniteSet(*a.poles)
    assert independent == a.solution
    assert inverse_set(m.stage.solution, m.scale, m.offset) == independent
    assert (
        sp.simplify(m.stage.original.subs(X, m.scale * X + m.offset) - a.original) == 0
    )
    assert {sp.simplify((p - m.offset) / m.scale) for p in m.stage.poles} == set(
        a.poles
    )


@pytest.mark.parametrize("row", SOURCES, ids=lambda r: r["task"])
def test_plans_replay_source_reuse_and_read_only_gateway(row):
    context = deepcopy(row["context"])
    p = plan(row, context)
    assert context == row["context"]
    assert computed_answer_set(p.answer) == answer_set(row["expected_answer"])
    assert all(
        not t["transformation_target_id"].startswith("section:condition")
        for t in p.transformations
    )
    source_ids = [
        a["asset_id"] for a in context["normalized_content"].get("assets", [])
    ]
    assert all(uid in p.solution_html for uid in source_ids)
    if row["task"] in ("511512", "511537"):
        assert len(handler(row).diagram_specs(context)) == 1
    else:
        assert not handler(row).diagram_specs(context)
    gateway = ReadOnlyGateway(context)
    record = _prepared_record(
        gateway,
        {"problem_id": context["problem_id"], "source_problem_id": row["task"]},
        None,
        handler(row).key,
        parent_solution_html=parent(row),
    )
    assert record["status"] == "prepared", record
    assert record["expected_answer"] == p.answer and record["transformations"] == list(
        p.transformations
    )
    assert len(gateway.reads) == 1 and gateway.ctx == context
    replay(context, p.transformations)
    assert not plan(row, context).transformations


@pytest.mark.parametrize(
    "row", [r for r in SOURCES if r["group"] == "508347"], ids=lambda r: r["task"]
)
def test_every_affine_proof_inequality_keeps_equivalence_and_centering(row):
    m = model(read(row["context"])[1], "affine_radical")
    html = plan(row, row["context"]).solution_html
    spans = BeautifulSoup(html, "html.parser").find_all(
        "span", attrs={"data-inline-latex": True}
    )
    midpoint = sp.simplify(sum(m.stage.poles) / 2)
    checked = 0
    for span in spans:
        formula = span["data-inline-latex"]
        if not re.search(r"\\(?:le|ge)(?![a-z])", formula):
            continue
        variable = "u" if re.search(r"\bu\b", formula) else "z"
        a = analyze(re.sub(r"\b" + variable + r"\b", "x", formula))
        expected = (
            inverse_set(m.stage.solution, 1, midpoint)
            if variable == "u"
            else m.stage.solution
        )
        assert a.solution == expected, (row["task"], formula)
        checked += 1
    assert checked == 6
    assert html.index("Возвращаясь") < html.index("Замечание.")
    assert "u=" in html and "z=" in html
    numerator, denominator = common_fraction(m.fractions, m.stage.right.value)
    assert sp.cancel(numerator / denominator - m.stage.original) == 0
    assert (
        sp.cancel(
            RationalParser(sp.latex(numerator / denominator)).parse().value
            - m.stage.original
        )
        == 0
    )


@pytest.mark.parametrize(
    "row", [r for r in SOURCES if r["group"] == "508397"], ids=lambda r: r["task"]
)
def test_reciprocal_system_rows_intersect_and_share_the_exact_parent_chart(row):
    m = model(read(row["context"])[1], "reciprocal_square")
    html = plan(row, row["context"]).solution_html
    assert sp.Intersection(*(a.solution for a in m.rows)) == m.stage.solution
    assert "7a4a4fc4-c0eb-4cf7-8d71-b1d602630908" in html
    assert not handler(row).diagram_specs(row["context"])
    assert r"\le|t|\le" in html
    formulas = [
        s["data-inline-latex"]
        for s in BeautifulSoup(html, "html.parser").find_all(
            "span", attrs={"data-inline-latex": True}
        )
    ]
    system = next(
        f for f in formulas if f.startswith(r"\begin{cases}") and r"\frac" in f
    )
    rows = (
        system.removeprefix(r"\begin{cases}").removesuffix(r"\end{cases}").split(r"\\")
    )
    assert len(rows) == 2
    computed = [analyze(re.sub(r"\bt\b", "x", formula)).solution for formula in rows]
    assert computed == [a.solution for a in m.rows]
    if row["task"] == "511525":
        assert len(handler(row).asset_requirements(row["context"])) == 1
    else:
        assert not handler(row).asset_requirements(row["context"])


@pytest.mark.parametrize(
    "task,points,closed,signs",
    [
        ("511512", ["-12", "-9", "-6", "-3"], {"-12", "-3"}, [1, -1, 1, -1, 1]),
        ("511537", ["1", "2", "3", "7/2"], {"1", "7/2"}, [1, -1, 1, -1, 1]),
    ],
)
def test_generated_chart_solves_for_z_and_preserves_open_poles(
    task, points, closed, signs
):
    row = next(r for r in SOURCES if r["task"] == task)
    (spec,) = handler(row).diagram_specs(row["context"])
    root = ET.fromstring(spec["svg_text"])
    marks = [n for n in root.iter() if n.get("data-boundary")]
    assert [m.get("data-boundary") for m in marks] == points
    assert {
        m.get("data-boundary") for m in marks if m.get("fill") == "#000000"
    } == closed
    assert [int(n.get("data-sign")) for n in root.iter() if n.get("data-sign")] == signs
    assert any(n.text == "z" for n in root.iter()) and not any(
        n.text == "x" for n in root.iter()
    )


@pytest.mark.parametrize(
    "formula,method",
    [
        (r"\frac{6}{x-3}+\frac{x-6}{x-9}\ge2", "affine_radical"),
        (
            r"\frac{6}{x\sqrt{3}-3}+\frac{x\sqrt{5}-6}{x\sqrt{3}-9}\ge2",
            "affine_radical",
        ),
        (r"(\frac{2}{x+3}+\frac{x+3}{3})^2\le\frac{25}{4}", "reciprocal_square"),
        (r"(\frac{2}{x+3}+\frac{x+3}{2})^2>\frac{25}{4}", "reciprocal_square"),
        (r"(\frac{-2}{x+3}-\frac{x+3}{2})^2\le\frac{25}{4}", "reciprocal_square"),
    ],
)
def test_unproved_substitutions_fail_closed(formula, method):
    with pytest.raises(UnsupportedCondition):
        model(analyze(formula), method)


@pytest.mark.parametrize(
    "change",
    ["bound", "unknown_asset", "wrong_variable", "wrong_parent", "extra_instruction"],
)
def test_unreviewed_chart_semantics_and_instructions_cannot_prepare(change):
    row = next(r for r in SOURCES if r["task"] == "508397")
    ctx = deepcopy(row["context"])
    if change == "bound":
        section = next(
            s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
        )
        section["html"] = section["html"].replace(r"\frac{25}{4}", r"\frac{49}{4}")
    elif change == "unknown_asset":
        ctx["normalized_content"]["assets"][0]["asset_id"] = "unknown"
    elif change == "wrong_variable":
        ctx["normalized_content"]["assets"][0]["asset_id"] = (
            "3c28bc07-a75e-444a-844a-a979c06f6a3f"
        )
    elif change == "extra_instruction":
        next(
            s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
        )["html"] += "<p>Укажите только целые решения.</p>"
    with pytest.raises(UnsupportedCondition):
        if change == "wrong_parent":
            handler(row).plan(PlanInput(ctx, parent_solution_html=parent(row) + " "))
        else:
            plan(row, ctx)
