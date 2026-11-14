"""All eight source conditions, three parent methods and the exact pre-domain chart."""

import hashlib
import json
import math
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
    _context_fingerprint,
    _prepared_record,
    _with_required_assets,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.logarithm_single_rationalization import analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.equations.single_log_three_methods_figures import (
    SOURCES,
    canonical,
    compatible,
)
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = json.loads(
    Path(__file__)
    .with_name("fixtures")
    .joinpath("single_log_three_methods_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {
    "508488": sp.Union(
        sp.Interval.open(-sp.oo, -1),
        sp.Interval.Ropen(-sp.Rational(1, 2), 0),
        sp.Interval.open(0, 1),
    ),
    "516932": sp.Interval.Ropen(-sp.Rational(3, 2), -sp.sqrt(2)),
    "508490": sp.Union(
        sp.Interval.open(-1, 0),
        sp.Interval.Lopen(0, sp.Rational(1, 2)),
        sp.Interval.open(1, sp.oo),
    ),
    "508515": sp.Union(sp.Interval.Lopen(-3, -2), sp.Interval.open(4, 5)),
    "508517": sp.Union(
        sp.Interval.Lopen(-sp.Rational(9, 2), -4), sp.Interval.open(6, 7)
    ),
    "508529": sp.Union(sp.Interval.Lopen(-4, -3), sp.Interval.open(3, 4)),
    "508574": sp.Interval.Lopen(2, 3),
    "513257": sp.Union(
        sp.Interval.open(3, 4), sp.Interval.Ropen(5, 6), sp.Interval.Lopen(6, 7)
    ),
}


def handler():
    return get_handler(get_group_profile("508488").content_rule_key)


def plan(row, context=None, parent=PARENT):
    ctx = _with_required_assets(
        row["context"] if context is None else context, handler().key
    )
    return handler().plan(PlanInput(ctx, parent_solution_html=parent))


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_manual_answers_complete_domains_and_direct_original_log_values(row):
    ctx, _ = canonical(row["context"])
    a = analyze(read_formula(ctx)[1])
    expected = MANUAL[row["task"]]
    same_set(a.solution, expected)
    same_set(answer_set(plan(row).answer), expected)
    same_set(
        a.domain,
        sp.Intersection(
            sp.solve_univariate_inequality(a.G > 0, X, relational=False),
            sp.solve_univariate_inequality(a.A > 0, X, relational=False),
        )
        - sp.FiniteSet(*sp.solve(a.G - 1, X)),
    )
    for point in [sp.Rational(i, 8) for i in range(-48, 65)]:
        B, Q = a.G.subs(X, point), a.A.subs(X, point)
        if B <= 0 or B == 1 or Q <= 0:
            assert not a.domain.contains(point)
            continue
        value = math.log(float(Q)) / math.log(float(B)) - float(a.bound)
        direct = value <= 1e-12 if a.operator == "<=" else value >= -1e-12
        assert bool(a.solution.contains(point)) == direct


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_three_methods_order_visible_repair_native_placement_and_readonly_replay(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == original and p.condition_html == row["expected_condition_html"]
    assert not handler().diagram_specs(ctx)
    sections = BeautifulSoup(p.solution_html, "html.parser").select(
        'section[data-content-kind="solution"]'
    )
    assert len(sections) == 2
    assert sections[0].get_text().index("Первый способ") < sections[0].get_text().index(
        "Второй способ"
    )
    text = sections[0].get_text()
    assert (
        text.index("Первый случай")
        < text.index("Второй случай")
        < text.index("Объединяем")
    )
    assert (
        "возрастает" in text
        and "убывает" in text
        and "методом рационализации" in sections[1].get_text()
    )
    if row["task"] == "513257":
        uid = row["context"]["normalized_content"]["assets"][0]["asset_id"]
        assert p.solution_html.count("<img ") == 1 and uid in str(sections[1])
        assert (
            str(sections[1]).index("полученное произведение")
            < str(sections[1]).index("<img ")
            < str(sections[1]).index("Учтём исходную")
        )
    else:
        assert "<img" not in p.solution_html
    changes = [
        t
        for t in p.transformations
        if t["transformation_target_id"].startswith("section:condition")
    ]
    assert len(changes) == (1 if row["task"] == "508488" else 0)
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
def test_saved_answer_and_unreviewed_parent_cannot_control_planning(row):
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), MANUAL[row["task"]])
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой родитель.</p>")


def test_source_base_exponent_is_a_visible_exact_condition_repair():
    row = ROWS[0]
    before = next(
        s["html"]
        for s in row["context"]["normalized_content"]["sections"]
        if s["key"] == "condition"
    )
    entry = SOURCES["condition_transcriptions"][
        hashlib.sha256(before.encode()).hexdigest()
    ]
    assert entry["before_html"] == before
    assert (
        entry["after_html"]
        == before.replace(r"\log_x^{2}", r"\log_{x^{2}}", 1)
        == row["expected_condition_html"]
    )
    assert (
        entry["source_url"].endswith("id=508488")
        and len(entry["source_svg_sha256"]) == 64
    )
    change = plan(row).transformations[0]
    assert (
        change["transformation_target_id"].startswith("section:condition")
        and change["value"]["html"] == entry["after_html"]
    )
    with pytest.raises(UnsupportedCondition):
        analyze(read_formula(row["context"])[1])


def test_native_cubic_chart_is_the_product_before_domain_not_the_final_solution():
    row = ROWS[-1]
    a = analyze(read_formula(row["context"])[1])
    uid, entry = next(iter(SOURCES["figures"].items()))
    assert sp.expand(a.product.original - (X - 4) * (X - 5) * (X - 7)) == 0
    assert compatible(entry, a) and entry["closed"] == [True, True, True]
    assert a.product.solution.contains(4) and not a.domain.contains(4)
    assert a.product.solution.contains(6) and not a.domain.contains(6)
    assert a.solution.contains(5) and a.solution.contains(7)
    asset = (
        Path(__file__).parents[3]
        / "src/solution_runner/pipelines/equations/assets/logarithmic-inequalities"
        / (uid + ".svg")
    )
    assert hashlib.sha256(asset.read_bytes()).hexdigest() == entry["sha256"]
    for field in ("role", "stage", "closed", "stage_solution"):
        altered = deepcopy(entry)
        altered[field] = "wrong"
        assert not compatible(altered, a)
    for field in ("points", "poles", "signs", "operator"):
        altered = deepcopy(entry)
        altered["stage"][field] = ["wrong"]
        assert not compatible(altered, a)


def test_missing_native_chart_is_restored_exactly_without_a_generated_copy():
    row = ROWS[-1]
    ctx = deepcopy(row["context"])
    uid = ctx["normalized_content"]["assets"][0]["asset_id"]
    ctx["normalized_content"]["assets"] = []
    restored = _with_required_assets(ctx, handler().key)
    assert restored["normalized_content"]["assets"][0]["asset_id"] == uid
    assert uid in plan(row, restored).solution_html and not handler().diagram_specs(
        restored
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "spacing",
        "instruction",
        "unknown_asset",
        "condition_asset",
        "incompatible_chart",
    ],
)
def test_unreviewed_condition_changes_and_assets_are_rejected(mutation):
    row = ROWS[-1] if mutation in ("incompatible_chart", "condition_asset") else ROWS[0]
    ctx = deepcopy(row["context"])
    condition = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    if mutation == "spacing":
        condition["html"] = condition["html"].replace("(x+1)", "(x +1)")
    elif mutation == "instruction":
        condition["html"] += "<p>Округлите ответ.</p>"
    elif mutation == "unknown_asset":
        ctx["normalized_content"]["assets"] = [
            {"asset_id": "unknown", "asset_key": "image_1"}
        ]
    elif mutation == "condition_asset":
        condition["asset_keys"] = ["image_1"]
    else:
        condition["html"] = condition["html"].replace("x-3", "x-2")
    original = deepcopy(ctx)
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
    assert ctx == original
