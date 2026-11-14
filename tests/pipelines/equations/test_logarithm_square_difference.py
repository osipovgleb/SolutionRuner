"""Keep both sign systems, every original exclusion and both diagram positions."""

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import sympy as sp
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
from solution_runner.pipelines.equations.logarithm_square_difference import analyze
from solution_runner.pipelines.equations.logarithm_square_difference_figures import (
    SOURCES,
    compatible,
)
from solution_runner.pipelines.equations.logarithm_square_difference_svg import (
    COLORS,
    Y,
    boundaries,
    render,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_square_difference_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)


def handler():
    return get_handler(get_group_profile("689017").content_rule_key)


def plan(row, context=None, parent=PARENT):
    ctx = _with_required_assets(
        row["context"] if context is None else context, handler().key
    )
    generated = tuple(
        {
            **spec,
            "source_asset_id": "preview-" + spec["sha256"][:16],
            "url": "/assets/preview-" + spec["sha256"][:16],
        }
        for spec in handler().diagram_specs(ctx)
    )
    return handler().plan(
        PlanInput(ctx, parent_solution_html=parent, generated_solution_assets=generated)
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_manual_answers_and_original_cubic_domains(row):
    a = analyze(read_formula(row["context"])[1])
    same_set(a.solution, answer_set(row["expected_answer"]))
    oracle = sp.Intersection(
        *(
            sp.solve_univariate_inequality(arg.value > 0, X, relational=False)
            - sp.FiniteSet(*arg.excluded)
            for arg in a.arguments
        )
    )
    same_set(a.domain, oracle)
    assert a.domain.contains(a.hole) is sp.false
    A, B = [arg.value for arg in a.arguments]
    assert (
        sp.cancel(a.ratio_root**2 - A / B) == 0
        and sp.cancel(a.product_root**2 - A * B) == 0
    )
    same_set(answer_set(plan(row).answer), a.solution)
    assert sum(branch.solution != sp.EmptySet for branch in a.systems) == (
        2 if row["task"] == "509424" else 1
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_actual_logarithm_squares_on_admissible_and_invalid_points(row):
    a = analyze(read_formula(row["context"])[1])
    A, B = [arg.value for arg in a.arguments]
    for point in (
        -9,
        -7,
        -5,
        -4,
        -3,
        -2,
        -1,
        sp.Rational(-4, 3),
        sp.Rational(-2, 3),
        0,
        1,
        3,
        4,
        5,
        7,
        8,
        9,
    ):
        if a.domain.contains(point) is not sp.true:
            assert a.solution.contains(point) is sp.false
            continue
        original = (sp.log(A.subs(X, point)) / sp.log(a.atoms[0].base)) ** 2 - (
            sp.log(B.subs(X, point)) / sp.log(a.atoms[1].base)
        ) ** 2
        value = sp.N(sp.simplify(sp.expand_log(original)), 50)
        assert bool(a.solution.contains(point)) == bool(
            value < 0 if a.operator == "<" else value > 0
        )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_runtime_replay_preserves_both_systems_and_diagram_order(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == original
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
    assert p.solution_html.count("<img ") == 2 and p.solution_html.index(
        "систему (1)"
    ) < p.solution_html.index("<img ") < p.solution_html.index("систему (2)")
    assert all(
        not t["transformation_target_id"].startswith("section:condition")
        for t in p.transformations
    )
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations
    for asset in original["normalized_content"]["assets"]:
        assert asset in ctx["normalized_content"]["assets"]


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
@pytest.mark.parametrize("index", [0, 1])
def test_generated_source_style_rows_are_mathematically_exact_and_not_cropped(
    row, index
):
    a = analyze(read_formula(row["context"])[1])
    branch = a.systems[index]
    root = ET.fromstring(render(a, index))
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert root.get("viewBox") == "0 0 500 194"
    bands = root.findall("s:rect", ns)
    assert {r.get("data-intersection") for r in bands} == {
        str(p) for p in sp.Union.make_args(branch.solution) if p != sp.EmptySet
    }
    circles = root.findall("s:circle", ns)
    expected = (
        boundaries(a.domain),
        set(branch.difference_stage.points),
        set(branch.sum_stage.points),
    )
    for y, points in zip(Y, expected, strict=True):
        markers = [c for c in circles if c.get("data-row-y") == str(y)]
        assert {c.get("data-boundary") for c in markers} == {str(p) for p in points}
        assert all(
            c.get("fill") == "white" and 0 < float(c.get("cx")) < 484 for c in markers
        )
    for stage, y in ((branch.difference_stage, Y[1]), (branch.sum_stage, Y[2])):
        signs = [
            int(t.get("data-sign"))
            for t in root.findall("s:text", ns)
            if t.get("data-row-y") == str(y)
        ]
        assert signs == list(stage.signs)
    assert set(COLORS) <= {el.get("stroke") for el in root.iter() if el.get("stroke")}
    assert all(float(t.get("y")) < 194 for t in root.findall("s:text", ns))


def test_parent_figures_are_reused_exactly_and_coarse_empty_branch_is_honest():
    row = ROWS[0]
    a = analyze(read_formula(row["context"])[1])
    assert not handler().diagram_specs(row["context"])
    p = plan(row)
    assert not any(
        t["transformation_target_id"].startswith("asset:") for t in p.transformations
    )
    for asset in row["context"]["normalized_content"]["assets"]:
        assert p.solution_html.count(asset["asset_id"]) == 2
    entry = next(e for e in SOURCES["figures"].values() if e["branch"] == 1)
    assert entry["omit_domain_hole"] and compatible(entry, a, 1)
    assert (
        sp.Intersection(
            a.coarse_domain,
            a.systems[1].sum_stage.solution,
            a.systems[1].difference_stage.solution,
        )
        == sp.EmptySet
    )
    altered = replace(a, coarse_domain=sp.S.Reals)
    assert not compatible(entry, altered, 1)


def test_missing_parent_figures_request_exact_reviewed_sources_instead_of_new_diagrams():
    ctx = deepcopy(ROWS[0]["context"])
    ctx["normalized_content"]["assets"] = []
    prepared = _with_required_assets(ctx, handler().key)
    assert {a["asset_id"] for a in prepared["normalized_content"]["assets"]} == set(
        SOURCES["figures"]
    )
    assert not handler().diagram_specs(prepared)


def test_daughter_requires_two_fresh_diagrams_and_stale_parent_diagrams_are_rejected():
    row = ROWS[1]
    assert len(handler().diagram_specs(row["context"])) == 2
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = deepcopy(
        ROWS[0]["context"]["normalized_content"]["assets"]
    )
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
    with pytest.raises(UnsupportedCondition):
        handler().plan(PlanInput(row["context"], parent_solution_html=PARENT))


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_2^2\frac{(x+2)^2(x+5)}{5}<\log_3^2\frac{x+5}{20}",
        r"\log_2\frac{(x+2)^2(x+5)}{5}<\log_2^2\frac{x+5}{20}",
        r"\log_2^2\frac{(x+2)^2(x+5)}{5}<\log_2^2\frac{x+5}{20}+x",
        r"\log_2^2\frac{(x+2)^2}{x+5}<\log_2^2\frac{x+5}{20}",
        r"\log_2^2\frac{(x+2)^2(x+5)}{5}\le\log_2^2\frac{x+5}{20}",
    ],
)
def test_unreviewed_square_shape_inequality_base_and_variables_are_rejected(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)


def test_saved_answer_is_not_an_input_and_parent_identity_is_required():
    row = ROWS[2]
    ctx = deepcopy(row["context"])
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] == "answer":
            section["html"] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), answer_set(row["expected_answer"]))
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой родитель.</p>")


@pytest.mark.parametrize(
    "field,value", [("kind", "unknown"), ("url", "/wrong"), ("asset_key", "wrong")]
)
def test_unknown_source_asset_metadata_is_rejected(field, value):
    row = ROWS[0]
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"][0][field] = value
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


def test_stale_generated_figure_checksum_is_rejected():
    row = ROWS[1]
    specs = handler().diagram_specs(row["context"])
    generated = tuple(
        {**spec, "sha256": "0" * 64, "source_asset_id": "wrong", "url": "/assets/wrong"}
        for spec in specs
    )
    with pytest.raises(UnsupportedCondition):
        handler().plan(
            PlanInput(
                row["context"],
                parent_solution_html=PARENT,
                generated_solution_assets=generated,
            )
        )


def test_long_exact_surd_labels_fail_closed_before_a_cropped_chart_is_prepared():
    a = analyze(r"\lg^{2}\frac{(x+1)^2(x+4)}{10000}<\lg^{2}\frac{x+4}{90000}")
    with pytest.raises(UnsupportedCondition, match="label exceeds"):
        render(a, 0)


def test_diagram_checksums_are_stable_across_independent_python_processes():
    import os
    import subprocess
    import sys

    import solution_runner.pipelines.equations.logarithm_square_difference as module

    source = """import json,sys
from pathlib import Path
from solution_runner.pipelines.equations.logarithm_square_difference_figures import diagram_specs
rows=json.loads(Path(sys.argv[1]).read_text())
print(json.dumps([s['sha256'] for row in rows for s in diagram_specs(row['context'])]))"""
    fixture = (
        Path(__file__).with_name("fixtures")
        / "logarithm_square_difference_sources.json"
    )
    outputs = [
        subprocess.check_output(
            [sys.executable, "-c", source, str(fixture)],
            env={
                **os.environ,
                "PYTHONHASHSEED": seed,
                "PYTHONPATH": str(Path(module.__file__).parents[3]),
            },
            text=True,
        )
        for seed in ("1", "2")
    ]
    assert outputs[0] == outputs[1]
