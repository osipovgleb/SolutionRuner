"""Coordinate checks, exact numeric figures and fail-closed section requests."""

from copy import deepcopy

import pytest
import sympy as sp
from adjacent_midpoint_source_cases import CASES, plan, read
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from midsection_geometry_oracle import verify
from test_pyramid_midsections_lifecycle import without_figures

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.distance_figures import prepare
from solution_runner.pipelines.solids.spatial_distance_model import condition_text

EXPECTED = {
    "500639": 8 * sp.sqrt(5),
    "507830": sp.sqrt(38),
    "511345": 2 * sp.sqrt(5),
    "511501": 3 * sp.sqrt(230),
}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_every_equality_exact_assets_and_repeat(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    m = prepare(ctx, ())[0]
    assert sp.simplify(m.answer - EXPECTED[case["task"]]) == 0
    assert sp.simplify(verify(solution_html(result), m) - m.answer) == 0
    assert ctx == case["context"]
    replay(ctx, result.transformations)
    assert (
        ctx["normalized_content"]["assets"]
        == case["context"]["normalized_content"]["assets"]
    )
    for key in ("condition", "source", "criteria"):
        assert section(ctx, key) == section(case["context"], key)
    assert not plan(case, ctx).transformations
    soup = BeautifulSoup(solution_html(result), "html.parser")
    assert len(soup.find_all("img")) == 1
    assert len(soup.select('ol[data-layout="source-subparts"] > li')) == 2


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_missing_figures_restore_compatible_dimensions_and_names(case):
    ctx = without_figures(case)
    result = plan(case, ctx)
    m = prepare(ctx, ())[0]
    verify(solution_html(result), m)
    replay(ctx, result.transformations)
    assert len(ctx["normalized_content"]["assets"]) == 1
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("factor", (sp.Rational(3, 2), 3))
def test_changed_dimensions_use_unnumbered_geometry_and_exact_scaling(case, factor):
    m = read(case["context"])
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    if "все ребра" in raw:
        old = "равны " + str(m.q["a"]) + "."
        new = "равны " + sp.latex(m.q["a"] * factor) + "."
    else:
        old = (
            "равно "
            + str(m.q["e"])
            + ", а сторона основания равна "
            + str(m.q["a"])
            + "."
        )
        new = (
            "равно "
            + sp.latex(m.q["e"] * factor)
            + ", а сторона основания равна "
            + sp.latex(m.q["a"] * factor)
            + "."
        )
    assert old in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, new) + "</p>"
    result = plan(case, ctx)
    scaled = prepare(ctx, ())[0]
    assert sp.simplify(scaled.answer - factor**2 * m.answer) == 0
    verify(solution_html(result), scaled)
    replay(ctx, result.transformations)
    assert (
        ctx["normalized_content"]["assets"][0]["asset_id"]
        == "c6006403-f34f-41d4-9a22-344d5709e7c7"
    )
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize(
    "task,old,new",
    (
        ("500639", r"1\colon 7", "1: 6"),
        ("507830", r"3\colon 1", "2: 1"),
        ("507830", "от вершины D", "от вершины B"),
        ("511501", "MK и SD", "MK и SC"),
        ("511501", "равно 13", "равно 8"),
        ("500639", "AB и BC", "AB и CD"),
    ),
)
def test_changed_claim_or_degenerate_pyramid_is_refused(task, old, new):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert old in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, new) + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_extra_request_and_parent_drift_are_refused(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Найдите также объём.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_html="changed")
