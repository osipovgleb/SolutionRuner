"""Every source, original rational holes and all rows of both parent-style charts."""

import hashlib
import json
import math
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from test_exam_trigonometric import replay
from test_exponential_inequality_preimages import answer_set
from test_exponential_inequality_quadratic import same_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import (
    _context_fingerprint,
    _prepared_record,
    _with_required_assets,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.logarithm_rational_base_cases import analyze
from solution_runner.pipelines.equations.logarithm_rational_base_figures import (
    SOURCES,
    canonical,
    compatible,
)
from solution_runner.pipelines.equations.logarithm_rational_base_svg import (
    render,
    signature,
)
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("logarithm_rational_base_cases_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
R = sp.sqrt(5)
COMMON = sp.Union(sp.Interval.open(-1, 0), sp.Interval.open(0, 1))
MANUAL = {
    "507893": sp.Union(
        sp.Interval.open((-1 - R) / 2, -1),
        sp.Interval.Lopen(0, sp.Rational(1, 3)),
        sp.Interval.open((-1 + R) / 2, 1),
        sp.Interval.open(1, sp.oo),
    ),
    "507921": sp.Union(
        sp.Interval.Ropen(-sp.Rational(4, 5), (1 - R) / 2),
        sp.Interval.open((1 + R) / 2, sp.oo),
    ),
    "508498": sp.Union(COMMON, sp.Interval.open(-2, -1), sp.Interval(2, sp.oo)),
    "508500": sp.Union(COMMON, sp.Interval(-sp.oo, -2), sp.Interval.open(1, 2)),
    "508506": sp.Union(COMMON, sp.Interval.open(-2, -1), sp.Interval(2, sp.oo)),
    "508508": sp.Union(COMMON, sp.Interval(-sp.oo, -2), sp.Interval.open(1, 2)),
    "511555": sp.Union(
        COMMON, sp.Interval.open(-sp.Rational(3, 2), -1), sp.Interval(3, sp.oo)
    ),
    "511557": sp.Union(
        COMMON, sp.Interval.open(-sp.Rational(3, 2), -1), sp.Interval(3, sp.oo)
    ),
}


def handler():
    return get_handler(get_group_profile("507893").content_rule_key)


def plan(row, context=None, parent=PARENT):
    h = handler()
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
        PlanInput(ctx, parent_solution_html=parent, generated_solution_assets=generated)
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_independent_answers_original_domains_and_logarithm_values(row):
    ctx, _ = canonical(row["context"])
    a = analyze(read_formula(ctx)[1])
    m = a.logarithm
    same_set(m.solution, MANUAL[row["task"]])
    same_set(answer_set(plan(row).answer), MANUAL[row["task"]])
    domain = sp.Intersection(
        sp.solve_univariate_inequality(m.G > 0, X, relational=False),
        sp.solve_univariate_inequality(m.A > 0, X, relational=False),
    ) - sp.FiniteSet(*sp.solve(m.G - 1, X))
    same_set(m.domain, domain)
    assert tuple(c.sign for c in a.cases) == (1, -1)
    for point in [sp.Rational(i, 8) for i in range(-48, 49)] + [sp.Rational(1, 3)]:
        if not domain.contains(point):
            continue
        value = math.log(float(m.A.subs(X, point))) / math.log(
            float(m.G.subs(X, point))
        ) - float(m.bound)
        direct = value <= 1e-12 if m.operator == "<=" else value >= -1e-12
        assert bool(m.solution.contains(point)) == direct


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_both_figures_precede_their_cases_and_runtime_is_readonly_and_idempotent(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == original and p.condition_html == row["expected_condition_html"]
    assert p.solution_html.count("<img ") == 2
    first = p.solution_html.index("<img ")
    second = p.solution_html.index("<img ", first + 1)
    assert (
        first
        < p.solution_html.index("Первый случай")
        < second
        < p.solution_html.index("Второй случай")
        < p.solution_html.index("Объединяем")
    )
    assert p.solution_html.index("возрастает") < p.solution_html.index("убывает")
    if row["task"] == "507921":
        assert "решений нет" in p.solution_html
    changes = [
        t
        for t in p.transformations
        if t["transformation_target_id"].startswith("section:condition")
    ]
    assert len(changes) == (1 if row["task"] in ("508506", "511557") else 0)
    if changes:
        assert (
            changes[0] == p.transformations[0]
            and changes[0]["value"]["html"] == row["expected_condition_html"]
        )
    gateway = ReadOnlyGateway(ctx)
    record = _prepared_record(
        gateway,
        {"problem_id": ctx["problem_id"], "source_problem_id": row["task"]},
        None,
        handler().key,
        parent_solution_html=PARENT,
    )
    assert record["status"] == "prepared" and record["transformations"] == list(
        p.transformations
    )
    assert record["input_fingerprint"] == _context_fingerprint(
        original
    ) and gateway.reads == [ctx["problem_id"]]
    replay(ctx, p.transformations)
    assert not plan(row, ctx).transformations


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_svg_rows_markers_signs_and_blue_intersections_match_every_system(row):
    ctx, _ = canonical(row["context"])
    a = analyze(read_formula(ctx)[1])
    for case in a.cases:
        svg = ET.fromstring(render(case))
        expected = signature(case)
        groups = [n for n in svg if n.get("data-row-index") is not None]
        assert len(groups) == (2 if case.sign == 1 else 3)
        for group, row_data in zip(groups, expected["rows"], strict=True):
            marks = [n for n in group.iter() if n.get("data-boundary") is not None]
            assert [n.get("data-boundary") for n in marks] == row_data["points"]
            assert [n.get("fill") == "#000000" for n in marks] == row_data["closed"]
            signs = [
                int(n.get("data-sign"))
                for n in group.iter()
                if n.get("data-sign") is not None
            ]
            assert signs == (row_data["signs"] or [])
        blue = {
            n.get("data-intersection")
            for n in svg
            if n.get("data-intersection") is not None
        }
        intervals = (
            set()
            if case.solution == sp.EmptySet
            else {str(v) for v in sp.Union.make_args(case.solution)}
        )
        assert blue == intervals
        assert sp.Intersection(*case.values) == case.solution


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_and_other_parent_cannot_choose_math_or_transcriptions(row):
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), MANUAL[row["task"]])
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой родитель.</p>")


def test_exact_parent_figures_and_every_plotted_row_property_are_certified():
    a = analyze(read_formula(ROWS[0]["context"])[1])
    assert not handler().diagram_specs(ROWS[0]["context"])
    for uid, entry in SOURCES["figures"].items():
        index = entry["branch"]
        assert compatible(entry, a, index)
        path = (
            Path(__file__).parents[3]
            / "src/solution_runner/pipelines/equations/assets/logarithmic-inequalities"
            / (uid + ".svg")
        )
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"]
        for field in ("role", "branch"):
            bad = deepcopy(entry)
            bad[field] = "wrong"
            assert not compatible(bad, a, index)
        for field in ("sign", "intersection"):
            bad = deepcopy(entry)
            bad["signature"][field] = "wrong"
            assert not compatible(bad, a, index)
        for row_index, row_data in enumerate(entry["signature"]["rows"]):
            for field in row_data:
                bad = deepcopy(entry)
                bad["signature"]["rows"][row_index][field] = "wrong"
                assert not compatible(bad, a, index)


@pytest.mark.parametrize("remove", [1, 2])
def test_missing_parent_sources_are_restored_without_generated_duplicates(remove):
    ctx = deepcopy(ROWS[0]["context"])
    ctx["normalized_content"]["assets"] = ctx["normalized_content"]["assets"][remove:]
    restored = _with_required_assets(ctx, handler().key)
    assert {v["asset_id"] for v in restored["normalized_content"]["assets"]} == set(
        SOURCES["figures"]
    )
    assert not handler().diagram_specs(restored)
    html = plan(ROWS[0], restored).solution_html
    assert all(html.count(uid) == 2 for uid in SOURCES["figures"])


def test_both_primary_fraction_transcriptions_are_exact_and_visible():
    for row in [v for v in ROWS if v["task"] in ("508506", "511557")]:
        before = next(
            s["html"]
            for s in row["context"]["normalized_content"]["sections"]
            if s["key"] == "condition"
        )
        entry = SOURCES["condition_transcriptions"][
            hashlib.sha256(before.encode()).hexdigest()
        ]
        n = "2" if row["task"] == "508506" else "3"
        assert (
            entry["before_html"] == before
            and entry["after_html"]
            == before.replace(
                r"\frac{" + n + r"}{x}^{2}", r"\frac{" + n + r"}{x^{2}}", 1
            )
            == row["expected_condition_html"]
        )
        assert (
            entry["source_url"].endswith("id=" + row["task"])
            and len(entry["source_svg_sha256"]) == 64
        )


def test_cancelled_original_poles_remain_in_both_cases_and_final_intersection():
    a = analyze(r"\log_{x^2+x}\frac{(x-1)^2(3x-1)}{3x-1}\le1")
    assert sp.Rational(1, 3) in a.logarithm.poles
    same_set(a.logarithm.solution, MANUAL["507893"] - sp.FiniteSet(sp.Rational(1, 3)))
    assert all(not c.solution.contains(sp.Rational(1, 3)) for c in a.cases)


@pytest.mark.parametrize(
    "mutation",
    [
        "unknown_asset",
        "incompatible_source",
        "condition_asset",
        "unknown_damage",
        "instruction",
    ],
)
def test_unreviewed_assets_and_damaged_formulas_are_rejected(mutation):
    row = (
        next(v for v in ROWS if v["task"] == "508506")
        if mutation == "unknown_damage"
        else ROWS[0]
    )
    ctx = deepcopy(row["context"])
    condition = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    if mutation == "unknown_asset":
        ctx["normalized_content"]["assets"].append(
            {"asset_id": "unknown", "asset_key": "image_3"}
        )
    elif mutation == "incompatible_source":
        condition["html"] = condition["html"].replace("x^{2}+x", "x^{2}-x")
    elif mutation == "condition_asset":
        condition["asset_keys"] = ["image_1"]
    elif mutation == "unknown_damage":
        condition["html"] = condition["html"].replace(
            r"\frac{2}{x}^{2}", r"\frac{2}{x}^{3}"
        )
    else:
        condition["html"] += "<p>Округлите ответ.</p>"
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
