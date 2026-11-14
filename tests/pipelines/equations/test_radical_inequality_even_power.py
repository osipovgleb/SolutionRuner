"""Original real-root domains, cancelled poles and both normalization directions."""

import json
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_exam_trigonometric import replay
from test_exponential_inequality_preimages import answer_set
from test_rational_inequality_preparation import ReadOnlyGateway

from solution_runner.pipelines.core.content_runtime import (
    _prepared_record,
    _with_required_assets,
)
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.equations.radical_inequality_even_power import analyze
from solution_runner.pipelines.equations.rational_inequality_figures import read_formula
from solution_runner.pipelines.equations.rational_inequality_parser import X
from solution_runner.pipelines.probability.common import UnsupportedCondition

ROWS = [
    r
    for r in json.loads(
        Path(__file__)
        .with_name("fixtures")
        .joinpath("radical_inequality_sources.json")
        .read_text()
    )
    if r["group"] == "507175"
]
PARENT = next(
    s["html"]
    for s in ROWS[0]["context"]["normalized_content"]["sections"]
    if s["key"] == "solution"
)
MANUAL = {
    "507175": (
        -1 - 2 * X,
        2 * X - 3 - 5 / X,
        14 / (X + 1) + 2,
        -1,
        -((2 * X - 5) ** 2) * (X + 3) / X,
        r"[-3;-1)\cup(-1;-1/2]",
    ),
    "507497": (
        -3 - 2 * X,
        2 * X + 1 - 6 / X,
        28 / (X + 2) - 2,
        -2,
        -((2 * X - 3) ** 2) * (X + 6) / X,
        r"[-6;-2)\cup(-2;-3/2]",
    ),
    "511414": (
        1 - 2 * X,
        2 * X - 1 - 3 / X,
        -15 / (X + 1) + 8,
        -1,
        -((2 * X - 3) ** 2) * (X - 2) / X,
        r"(0;1/2]",
    ),
    "511435": (
        -3 + 2 * X,
        2 * X - 1 - 10 / X,
        9 / (X + 2) - 4,
        -2,
        (2 * X - 5) ** 2 * (X + 1) / X,
        r"[3/2;\infty)",
    ),
}


def handler():
    return get_handler(get_group_profile("507175").content_rule_key)


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
def test_whole_projection_original_domain_and_independent_rational_oracle(row):
    a = analyze(read_formula(row["context"])[1])
    P, L, T, h, projection, answer = MANUAL[row["task"]]
    assert a.radicand == P
    assert sp.cancel(a.stage.original - projection) == 0
    assert sp.cancel(L * (T + P) - projection) == 0
    D = sp.solve_univariate_inequality(P >= 0, X, relational=False) - sp.FiniteSet(0, h)
    assert a.constraints.values == D and a.constraints.excluded == (h, 0)
    assert a.stage.holes == (h,) and a.stage.poles == (h, 0)
    oracle = sp.solve_univariate_inequality(
        projection >= 0, X, relational=False
    ).intersect(D)
    assert a.solution == oracle == answer_set(answer)
    assert answer_set(plan(row).answer) == oracle


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_original_root_values_on_real_domain_and_original_undefined_factors(row):
    a = analyze(read_formula(row["context"])[1])
    P, L, T, h, _projection, _answer = MANUAL[row["task"]]
    for point in {sp.Rational(n, 4) for n in range(-32, 33)} | set(a.stage.points):
        if a.constraints.values.contains(point) is not sp.true:
            assert a.solution.contains(point) is sp.false
            continue
        value = sp.simplify(
            L.subs(X, point) * (T.subs(X, point) + sp.sqrt(P.subs(X, point)) ** 2)
        )
        assert bool(a.solution.contains(point)) == bool(value >= 0)
    assert sp.simplify(L.subs(X, h)) == 0
    assert a.stage.original.subs(X, h).is_finite is True
    assert not a.solution.contains(h)


def test_even_power_projection_does_not_make_a_nonreal_original_root_valid():
    a = analyze(read_formula(ROWS[0]["context"])[1])
    assert a.stage.solution.contains(sp.Rational(5, 2))
    assert a.radicand.subs(X, sp.Rational(5, 2)) < 0
    assert not a.solution.contains(sp.Rational(5, 2))


def test_positive_slope_and_projection_do_not_inherit_the_parent_sign_flip():
    row = ROWS[-1]
    a = analyze(read_formula(row["context"])[1])
    assert a.radicand.coeff(X) == 2 and a.stage.sign_operator == ">="
    assert a.solution == sp.Interval(sp.Rational(3, 2), sp.oo)
    assert a.solution.contains(sp.Rational(5, 2))
    assert "знак неравенства меняется" not in plan(row).solution_html
    assert analyze(read_formula(ROWS[0]["context"])[1]).stage.sign_operator == "<="


def test_cancelled_original_pole_inside_a_radicand_is_also_retained():
    formula = read_formula(ROWS[0]["context"])[1].replace(
        "-1-2x", r"\frac{x+2}{x+2}-2-2x"
    )
    a = analyze(formula)
    assert a.radicand == -1 - 2 * X
    assert a.stage.holes == (-2, -1)
    assert not a.solution.contains(-2)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_parent_expansion_cancellation_and_chart_order_readonly_replay(row):
    ctx = deepcopy(row["context"])
    original = deepcopy(ctx)
    p = plan(row, ctx)
    assert ctx == original
    assert p.solution_html.count("<img ") == 1
    assert "\\" not in BeautifulSoup(p.solution_html, "html.parser").get_text()
    assert (
        p.solution_html.index("Квадрат арифметического корня")
        < p.solution_html.index("раскроем скобки")
        < p.solution_html.index("Сокращаем")
        < p.solution_html.index("<img ")
        < p.solution_html.index("Учитывая исходное ограничение")
    )
    assert not any(
        t["transformation_target_id"].startswith("section:condition")
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
    assert all(
        v in ctx["normalized_content"]["assets"]
        for v in original["normalized_content"]["assets"]
    )


@pytest.mark.parametrize("row", ROWS[:2], ids=lambda r: r["task"])
def test_exact_native_chart_is_restored_instead_of_generated_if_missing(row):
    uid = row["context"]["normalized_content"]["assets"][0]["asset_id"]
    assert uid in plan(row).solution_html
    assert not handler().diagram_specs(row["context"])
    ctx = deepcopy(row["context"])
    ctx["normalized_content"]["assets"] = []
    prepared = _with_required_assets(ctx, handler().key)
    assert prepared["normalized_content"]["assets"][0]["asset_id"] == uid
    assert not handler().diagram_specs(prepared)


@pytest.mark.parametrize(
    "task,points,signs",
    [
        (
            "511414",
            [("-1", "#FFFFFF"), ("0", "#FFFFFF"), ("3/2", "#000000"), ("2", "#000000")],
            [1, 1, -1, -1, 1],
        ),
        (
            "511435",
            [
                ("-2", "#FFFFFF"),
                ("-1", "#000000"),
                ("0", "#FFFFFF"),
                ("5/2", "#000000"),
            ],
            [1, 1, -1, 1, 1],
        ),
    ],
)
def test_new_fraction_labelled_global_chart_keeps_holes_and_double_zeros(
    task, points, signs
):
    row = next(r for r in ROWS if r["task"] == task)
    specs = handler().diagram_specs(row["context"])
    assert len(specs) == 1
    root = ET.fromstring(specs[0]["svg_text"])
    ns = {"s": "http://www.w3.org/2000/svg"}
    assert [
        (c.get("data-boundary"), c.get("fill")) for c in root.findall("s:circle", ns)
    ] == points
    assert [
        int(t.get("data-sign"))
        for t in root.findall("s:text", ns)
        if t.get("data-sign")
    ] == signs
    assert root.get("data-source-style") == "b113407d-cfad-4010-9a7d-54a053b6e0dc"
    fraction_marker = next(
        c for c in root.findall("s:circle", ns) if "/" in c.get("data-boundary")
    )
    labels = [
        t
        for t in root.findall("s:text", ns)
        if t.get("x") == fraction_marker.get("cx") and not t.get("data-sign")
    ]
    assert (
        min(float(t.get("y")) for t in labels) - float(fraction_marker.get("cy")) >= 18
    )
    assert all(
        float(t.get("y")) < float(root.get("height"))
        for t in root.findall("s:text", ns)
    )


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["task"])
def test_saved_answer_is_ignored_and_other_parent_is_rejected(row):
    ctx = deepcopy(row["context"])
    next(s for s in ctx["normalized_content"]["sections"] if s["key"] == "answer")[
        "html"
    ] = "<p>999</p>"
    assert answer_set(plan(row, ctx).answer) == answer_set(MANUAL[row["task"]][-1])
    with pytest.raises(UnsupportedCondition):
        plan(row, parent="<p>Другой метод.</p>")


@pytest.mark.parametrize(
    "field,value",
    [
        ("asset_key", "wrong"),
        ("kind", None),
        ("url", "/wrong"),
        ("asset_id", "unknown"),
    ],
)
def test_native_chart_requires_verified_metadata(field, value):
    ctx = deepcopy(ROWS[0]["context"])
    ctx["normalized_content"]["assets"][0][field] = value
    with pytest.raises(UnsupportedCondition):
        plan(ROWS[0], ctx)


@pytest.mark.parametrize(
    "before,after",
    [
        ("^{2}", "^{3}"),
        ("+(\\sqrt", "+2(\\sqrt"),
        ("-1-2x", "x^2+1"),
        ("14}{x+1", "14}{x+2"),
        ("\\ge 0", "\\le 0"),
        ("\\ge 0", "\\ge 1"),
    ],
)
def test_unknown_powers_radicands_cancellation_and_whole_comparison_are_rejected(
    before, after
):
    formula = read_formula(ROWS[0]["context"])[1]
    mutated = formula.replace(before, after)
    assert mutated != formula
    with pytest.raises(UnsupportedCondition):
        analyze(mutated)
