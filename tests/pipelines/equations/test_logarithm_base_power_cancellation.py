"""Both parent methods, six original domains and an explicit primary base repair."""

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
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.logarithm_base_power_cancellation import (
    analyze,
)
from solution_runner.pipelines.equations.logarithm_base_power_cancellation_proof import (
    SOURCES,
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
    .joinpath("logarithm_base_power_cancellation_sources.json")
    .read_text()
)
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {
    "508513": (
        4 - X,
        X + 5,
        8,
        -1,
        -5,
        4,
        sp.Union(sp.Interval.Lopen(-5, -4), sp.Interval.open(3, 4)),
    ),
    "508531": (
        4 - X,
        X + 5,
        -1,
        1,
        -5,
        4,
        sp.Union(sp.Interval.Lopen(-5, -4), sp.Interval.open(3, 4)),
    ),
    "508533": (5 - X, X + 2, -4, 1, -2, 5, sp.Interval.Ropen(-1, 4)),
    "508535": (3 - X, X + 4, -2, 1, -4, 3, sp.Interval.Ropen(-3, 2)),
    "508579": (5 - X, X + 4, -10, 1, -4, 5, sp.Interval.Ropen(-3, 4)),
    "511565": (4 - X, X + 1, -4, 1, -1, 4, sp.Interval.Ropen(0, 3)),
}


def handler():
    return get_handler(get_group_profile("508513").content_rule_key)


def plan(row, context=None, parent=PARENT):
    return handler().plan(
        PlanInput(
            row["context"] if context is None else context, parent_solution_html=parent
        )
    )


def canonical(row):
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition")[
        "html"
    ] = row["expected_condition_html"]
    return ctx


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_manual_original_domains_answers_and_complete_logarithm_identity(row):
    a = analyze(read_formula(canonical(row))[1])
    B, H, bound, sign, lower, upper, expected = MANUAL[row["task"]]
    assert (a.base, a.linear, a.bound, a.sign) == (B, H, bound, sign)
    same_set(
        a.logarithm.domain, sp.Interval.open(lower, upper) - sp.FiniteSet(upper - 1)
    )
    same_set(a.logarithm.solution, expected)
    same_set(answer_set(plan(row).answer), expected)
    assert sp.cancel(a.argument.value - B**bound * H**sign) == 0
    for point in [sp.Rational(i, 8) for i in range(-48, 57)]:
        if not a.logarithm.domain.contains(point):
            continue
        b, q = float(B.subs(X, point)), float(a.argument.value.subs(X, point))
        value = math.log(q) / math.log(b)
        reduced = bound + sign * math.log(float(H.subs(X, point))) / math.log(b)
        assert abs(value - reduced) < 1e-10
        direct = (
            value >= bound - 1e-12 if a.operator == ">=" else value <= bound + 1e-12
        )
        assert bool(a.logarithm.solution.contains(point)) == direct


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_log_property_then_below_first_cases_and_supplemental_product_readonly(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == original and not handler().diagram_specs(ctx)
    assert (
        p.condition_html == row["expected_condition_html"]
        and "<img" not in p.solution_html
    )
    sections = BeautifulSoup(p.solution_html, "html.parser").select(
        'section[data-content-kind="solution"]'
    )
    assert len(sections) == 2
    first = sections[0].get_text()
    assert (
        first.index("свойства логарифма")
        < first.index("Первый случай")
        < first.index("Второй случай")
        < first.index("Объединяем")
    )
    assert first.index("убывает") < first.index("возрастает")
    assert (
        "Первый способ" not in first
        and "методом рационализации" in sections[1].get_text()
    )
    changes = [
        t
        for t in p.transformations
        if t["transformation_target_id"].startswith("section:condition")
    ]
    assert len(changes) == (1 if row["task"] == "508579" else 0)
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
def test_wrong_saved_answer_and_parent_do_not_choose_the_result(row):
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    same_set(answer_set(plan(row, ctx).answer), MANUAL[row["task"]][-1])
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой родитель.</p>")


def test_the_base_grouping_repair_is_visible_exact_and_primary_evidenced():
    row = next(v for v in ROWS if v["task"] == "508579")
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
        == before.replace(r"\log_5-x", r"\log_{(5-x)}", 1)
        == row["expected_condition_html"]
    )
    assert (
        entry["source_url"].endswith("id=508579")
        and len(entry["source_svg_sha256"]) == 64
    )
    with pytest.raises(UnsupportedCondition):
        analyze(read_formula(row["context"])[1])
    with pytest.raises(UnsupportedCondition):
        RationalParser(r"(x-5)^{10}").parse()
    assert analyze(read_formula(canonical(row))[1]).bound == -10


def test_a_cancelled_original_hole_removes_an_included_endpoint():
    a = analyze(r"\log_{4-x}\frac{(x-4)^8(x+4)}{(x+5)(x+4)}\ge8")
    assert -4 in a.argument.excluded and -4 in a.logarithm.poles
    same_set(
        a.logarithm.solution, sp.Union(sp.Interval.open(-5, -4), sp.Interval.open(3, 4))
    )


@pytest.mark.parametrize("mutation", ["spacing", "instruction", "asset"])
def test_unreviewed_damage_and_assets_do_not_receive_a_guessed_repair(mutation):
    row = next(v for v in ROWS if v["task"] == "508579")
    ctx = deepcopy(row["context"])
    condition = next(
        s for s in ctx["normalized_content"]["sections"] if s["key"] == "condition"
    )
    if mutation == "spacing":
        condition["html"] = condition["html"].replace(r"\log_5-x", r"\log_5 -x")
    elif mutation == "instruction":
        condition["html"] += "<p>Округлите ответ.</p>"
    else:
        ctx["normalized_content"]["assets"] = [
            {"asset_id": "unknown", "asset_key": "image_1"}
        ]
    original = deepcopy(ctx)
    with pytest.raises(UnsupportedCondition):
        plan(row, ctx)
    assert ctx == original


@pytest.mark.parametrize(
    "formula",
    [
        r"\log_{x-4}\frac{(x-4)^8}{x+5}\ge8",
        r"\log_{(4-x)^2}\frac{(x-4)^8}{x+5}\ge8",
        r"\log_{4-x}\frac{(x-4)^8}{x^2+5}\ge8",
        r"\log_{4-x}\frac{(x-4)^8}{5-x}\ge8",
        r"\log_{4-x}\frac{(x-4)^8}{x+5}\ge7",
        r"\log_{4-x}\frac{(x-4)^8}{x+5}+1\ge8",
        r"2\log_{4-x}\frac{(x-4)^8}{x+5}\ge8",
        r"\log_{4-x}\frac{(x-4)^8}{x+5}+x\ge8",
        r"\log_{4-x}\frac{(x-4)^{11}}{x+5}\ge11",
        r"\log_{4-x}\frac{(x-4)^8}{x+5}\ge x",
    ],
)
def test_the_whole_base_level_argument_and_affine_factor_identity_are_required(formula):
    with pytest.raises(UnsupportedCondition):
        analyze(formula)
