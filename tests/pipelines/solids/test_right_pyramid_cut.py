"""Coordinate checks, exact numeric figures and fail-closed section requests."""

import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from right_pyramid_cut_geometry_oracle import verify
from right_pyramid_cut_source_cases import CASES, plan, read
from test_pyramid_midsections_lifecycle import without_figures

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.distance_figures import prepare
from solution_runner.pipelines.solids.spatial_distance_model import condition_text

EXPECTED = {
    "505471": sp.sqrt(15) / 2,
    "505493": 2 * sp.sqrt(22),
    "505499": 2 * sp.sqrt(3),
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
    assert len(soup.find_all("img")) == len(ctx["normalized_content"]["assets"])
    assert len(soup.select('ol[data-layout="source-subparts"] > li')) == 2


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_missing_figures_restore_compatible_dimensions_and_names(case):
    ctx = without_figures(case)
    result = plan(case, ctx)
    m = prepare(ctx, ())[0]
    verify(solution_html(result), m)
    replay(ctx, result.transformations)
    assert len(ctx["normalized_content"]["assets"]) == len(
        case["context"]["normalized_content"]["assets"]
    )
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("factor", (sp.Rational(3, 2), 3))
def test_scaling_preserves_all_reviewed_geometry_and_methods(case, factor):
    ctx = deepcopy(case["context"])
    m = read(ctx)
    raw = condition_text(section(ctx, "condition")["html"], None)
    numbers = re.findall(r"(?<![A-Z0-9])\d+(?![A-Z0-9])", raw)
    assert len(numbers) == 4
    raw = re.sub(
        r"(?<![A-Z0-9])\d+(?![A-Z0-9])",
        lambda v: sp.latex(sp.Integer(v[0]) * factor),
        raw,
    )
    section(ctx, "condition")["html"] = "<p>" + raw + "</p>"
    result = plan(case, ctx)
    changed = prepare(ctx, ())[0]
    assert sp.simplify(changed.answer - factor**2 * m.answer) == 0
    verify(solution_html(result), changed)
    replay(ctx, result.transformations)
    assert (
        ctx["normalized_content"]["assets"]
        == case["context"]["normalized_content"]["assets"]
    )
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize("e", ("15", r"4\sqrt{6}"))
def test_midpoint_main_cosine_method_survives_changed_side_equalities(e):
    case = next(c for c in CASES if c["task"] == "505493")
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    section(ctx, "condition")["html"] = (
        "<p>" + raw.replace("MA равно 11", "MA равно " + e) + "</p>"
    )
    result = plan(case, ctx)
    verify(solution_html(result), prepare(ctx, ())[0])
    assert "косинус угла FED" in solution_html(result)


@pytest.mark.parametrize(
    "task,old,new",
    (
        ("505471", "и BE = 1", "и BE = 2"),
        ("505471", "ребро MB перпендикулярно", "ребро MC перпендикулярно"),
        ("505493", "F — середина AM", "F — середина MB"),
        ("505499", "ребро MA перпендикулярно", "ребро MB перпендикулярно"),
        ("505499", "ребро MB равно 5", "ребро MB равно 2"),
        ("505499", "BE = ML = 1", "BE = ML = 6"),
    ),
)
def test_changed_claim_or_invalid_geometry_is_refused(task, old, new):
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
