"""Polynomial division, retained holes, two valid methods and source-axis correction."""

import gzip
import hashlib
import json
import xml.etree.ElementTree as ET
from copy import deepcopy
from itertools import pairwise
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
from solution_runner.pipelines.equations.rational_exponential_division import (
    METHODS,
    cube_grouping,
    roots,
)
from solution_runner.pipelines.equations.rational_exponential_division_figures import (
    SOURCES,
    corrected,
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
    .joinpath("rational_exponential_division_sources.json")
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
METHOD = {
    "514448": "affine_division",
    "514618": "contained_cancellation",
    "514625": "cubic_division",
}


def handler(row):
    return get_handler(get_group_profile(row["group"]).content_rule_key)


def model(row):
    return analyze(read_formula(row["context"])[1])


def prepared(row, ctx):
    h = handler(row)
    ctx = _with_required_assets(ctx, h.key)
    specs = h.diagram_specs(ctx)
    generated = tuple(
        {
            **spec,
            "source_asset_id": "preview-" + spec["sha256"][:16],
            "url": "/assets/preview-" + spec["sha256"][:16],
        }
        for spec in specs
    )
    return ctx, generated


def plan(row, ctx=None, parent=None):
    ctx, generated = prepared(row, ctx or row["context"])
    return handler(row).plan(
        PlanInput(
            ctx,
            parent_solution_html=parent or PARENTS[row["group"]],
            generated_solution_assets=generated,
        )
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_all_actual_answers_original_domains_and_independent_cas(row):
    a = model(row)
    relation = {"<=": sp.Le, ">=": sp.Ge, "<": sp.Lt, ">": sp.Gt}[a.operator]
    independent = sp.solve_univariate_inequality(
        relation(a.stage.original, 0), X, relational=False
    ) - sp.FiniteSet(*a.stage.holes)
    same_set(independent, a.stage.solution)
    if row["task"] == "667678":
        expected = sp.Union(
            sp.Interval.open(-1, 1),
            sp.Interval.Ropen(sp.log(1 + sp.sqrt(321)) / sp.log(2) - 3, 2),
        )
    else:
        expected = answer_set(
            row["expected_answer"].replace(r"\left", "").replace(r"\right", "")
        )
    same_set(a.solution, expected)
    assert plan(row).answer == a.answer
    for t, level, points in a.back:
        assert sp.simplify(a.base**level - t) == 0
        assert (
            len(points) == 1 and sp.simplify(a.exponent.subs(X, points[0]) - level) == 0
        )
    assert all(a.stage.solution.contains(h) is sp.false for h in a.stage.holes)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_every_division_identity_and_algebraic_step_is_exact(row):
    a = model(row)
    identities, steps = METHODS[METHOD[row["group"]]](a.stage)
    for _, left, right in identities:
        assert sp.expand(left - right) == 0
    for item in steps:
        value = RationalParser(item.text).parse().value
        assert sp.cancel(value - a.stage.original) == 0, (row["task"], item.text)
        assert sp.cancel(item.value - a.stage.original) == 0
    grouping = cube_grouping(a.stage)
    if grouping:
        for item in grouping:
            assert (
                sp.cancel(RationalParser(item.text).parse().value - a.stage.original)
                == 0
            )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_readonly_runtime_condition_immutability_and_replay(row):
    ctx = deepcopy(row["context"])
    p = plan(row, ctx)
    h = handler(row)
    assert ctx == row["context"]
    assert all(
        not t["transformation_target_id"].startswith("section:condition")
        for t in p.transformations
    )
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        h.key,
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


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_algebra_method_domains_and_figure_roles(row):
    p = plan(row)
    a = model(row)
    specs = handler(row).diagram_specs(row["context"])
    if row["group"] == "514448":
        assert not specs
        if not row["context"]["normalized_content"]["assets"]:
            assert "<img " not in p.solution_html
        assert "делением многочленов" in p.solution_html
    else:
        if a.stage.holes:
            assert "Сокращение множителя не возвращает" in p.solution_html
    if row["task"] in ("514618", "514632", "660734"):
        assert len(specs) == 1 and "preview-" in p.solution_html
        assert any(
            t["transformation_target_id"].startswith("asset:")
            for t in p.transformations
        )
    if row["task"] in ("660762", "667678", "660733", "660773"):
        assert (
            not specs
            and row["context"]["normalized_content"]["assets"][0]["asset_id"]
            in p.solution_html
        )
        assert all(
            not t["transformation_target_id"].startswith("asset:")
            for t in p.transformations
        )
    assert p.solution_html.count("<img ") == int(
        row["group"] == "514618" or bool(row["context"]["normalized_content"]["assets"])
    )


def test_both_valid_native_methods_are_selected_by_exact_cube_structure():
    row = next(r for r in ROWS if r["task"] == "660734")
    a = model(row)
    assert cube_grouping(a.stage) is not None
    p = plan(row)
    assert p.solution_html.count("<strong>") == 2
    first, second = p.solution_html.split("<p><strong>Второй способ.</strong></p>")
    assert "разность кубов" in first and "вложенными знаменателями" in second
    assert p.solution_html.count("<img ") == 1
    assert (
        cube_grouping(model(next(r for r in ROWS if r["task"] == "660762")).stage)
        is None
    )


def test_division_keeps_constant_residual_and_fully_cancelled_original_hole():
    constant = model(next(r for r in ROWS if r["task"] == "514644"))
    _, steps = METHODS["affine_division"](constant.stage)
    assert sp.cancel(steps[0].value - (14 + 2 / (X - 1) + 99 / (X - 7))) == 0
    hole = next(r for r in ROWS if r["task"] == "655097")
    a = model(hole)
    assert a.stage.holes == (sp.Integer(3),)
    assert a.solution.contains(1) is sp.false
    assert r"t\ne 3" in plan(hole).solution_html


def test_irrational_log_bound_discriminant_and_exact_point_order_are_shown():
    row = next(r for r in ROWS if r["task"] == "667678")
    a = model(row)
    html = roots(a.stage, "t")
    assert "321" in html and r"\pm" in html and "дискриминанту" in html
    soup = BeautifulSoup(html, "html.parser")
    order = soup.find_all(attrs={"data-inline-latex": True})[-1]["data-inline-latex"]
    values = [RationalParser(v).parse().value for v in order.split("<")]
    assert all(sp.simplify(right - left) > 0 for left, right in pairwise(values))
    expected = sp.log(1 + sp.sqrt(321)) / sp.log(2) - 3
    assert any(
        sp.simplify(sp.expand_log(v - expected, force=True)) == 0
        for v in a.solution.boundary
    )


def test_corrected_svg_preserves_every_element_except_the_certified_axis_path():
    from solution_runner.pipelines.equations.rational_exponential_division_figures import (
        DIRECTORY,
    )

    entry = SOURCES["figures"]["8f36f991-9665-4b5a-b7e9-1f54bc254b2a"]
    root = ET.fromstring(
        gzip.decompress(
            (DIRECTORY / "rational-inequalities" / entry["prepared_file"]).read_bytes()
        )
    )
    items = []
    path_index = -1
    for node in root.iter():
        attrs = dict(node.attrib)
        if node.tag.endswith("path"):
            path_index += 1
            if path_index == entry["axis_path_index"]:
                attrs.pop("d")
        items.append((node.tag, sorted(attrs.items()), (node.text or "").strip()))
    assert (
        hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()
        == entry["structure_without_axis_sha256"]
    )


@pytest.mark.parametrize(
    "row",
    [r for r in ROWS if r["context"]["normalized_content"]["assets"]],
    ids=lambda r: r["task"],
)
def test_unknown_relabelled_or_duplicate_image_fails_closed(row):
    for field, value in [
        ("asset_id", "unknown"),
        ("asset_key", "wrong"),
        ("kind", "wrong"),
        ("url", "/assets/foreign"),
    ]:
        ctx = deepcopy(row["context"])
        ctx["normalized_content"]["assets"][0][field] = value
        with pytest.raises(UnsupportedCondition):
            plan(row, ctx)
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] *= 2
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)


def test_corrupted_corrected_svg_certificate_is_rejected(monkeypatch):
    key = "8f36f991-9665-4b5a-b7e9-1f54bc254b2a"
    entry = SOURCES["figures"][key]
    monkeypatch.setitem(entry, "prepared_sha256", "wrong")
    with pytest.raises(UnsupportedCondition):
        corrected(entry)


def test_foreign_parent_and_parent_method_mismatch_rejected():
    row = ROWS[0]
    with pytest.raises(UnsupportedCondition):
        plan(row, parent=PARENTS[row["group"]] + "wrong")
    other = next(r for r in ROWS if r["group"] == "514625")
    with pytest.raises(UnsupportedCondition):
        plan(row, parent=PARENTS[other["group"]])


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_unknown_answers_do_not_drive_calculation(row):
    ctx = deepcopy(row["context"])
    for section in ctx["normalized_content"]["sections"]:
        if section["key"] in ("answer", "solution"):
            section["html"] = "<p>wrong</p>"
    assert plan(row, ctx).answer == plan(row).answer


def test_fraction_labels_have_enough_canvas_height_and_large_labels_fail_closed():
    from solution_runner.pipelines.equations.rational_exponential_holes_svg import (
        render,
    )
    from solution_runner.pipelines.equations.rational_inequality import (
        analyze as rational,
    )

    stage = rational(r"\frac{(x-1)(2x-1)(2x-3)}{(x-1)(x-2)}\le 0")
    root = ET.fromstring(render(stage))
    assert float(root.get("height")) >= 54
    assert all(
        float(n.get("y", "0")) < float(root.get("height"))
        for n in root.iter()
        if n.tag.endswith("text")
    )
    large = rational(r"\frac{(x-1)(x-1000)(x-2000)}{(x-1)(x-3)}\le 0")
    with pytest.raises(UnsupportedCondition):
        render(large)
