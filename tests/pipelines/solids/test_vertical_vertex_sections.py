"""Coordinate checks, exact numeric figures and fail-closed section requests."""

from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from midsection_geometry_oracle import verify
from test_pyramid_midsections_lifecycle import without_figures
from vertical_cut_source_cases import CASES, plan, read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.distance_figures import prepare

EXPECTED = {
    "562034": 30 * sp.sqrt(17) / 7,
    "656085": 476 * sp.sqrt(34) / 23,
    "656255": 65 * sp.sqrt(217) / 17,
    "670279": 120 * sp.sqrt(17) / 7,
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
    assert len(ctx["normalized_content"]["assets"]) == 1
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("factor", (sp.Rational(3, 2), 3))
def test_scaled_conditions_keep_both_methods_and_exact_geometry(case, factor):
    ctx = deepcopy(case["context"])
    m = read(ctx)
    a, e, am, sk = (dict(m.given)[key] * factor for key in ("a", "e", "AM", "SK"))
    section(ctx, "condition")["html"] = condition(a, e, am, sk)
    result = plan(case, ctx)
    scaled = prepare(ctx, ())[0]
    assert sp.simplify(scaled.answer - factor**2 * m.answer) == 0
    verify(solution_html(result), scaled)
    replay(ctx, result.transformations)
    assert (
        ctx["normalized_content"]["assets"]
        == case["context"]["normalized_content"]["assets"]
    )
    assert not plan(case, ctx).transformations


def condition(a, e, am, sk):
    return (
        "<p>В правильной четырехугольной пирамиде SABCD сторона основания AB равна "
        + sp.latex(a)
        + ", а боковое ребро SA равно "
        + sp.latex(e)
        + ". На ребрах AB и SB отмечены точки M и K соответственно, причем AM = "
        + sp.latex(am)
        + ", SK = "
        + sp.latex(sk)
        + ". Плоскость α перпендикулярна плоскости ABC и содержит точки M и K. Докажите, что плоскость α содержит точку C. Найдите площадь сечения пирамиды SABCD плоскостью α.</p>"
    )


@pytest.mark.parametrize("a,e,am,sk", ((10, 17, 3, 3), (6, 10, 2, 2), (4, 7, 1, 1)))
@pytest.mark.parametrize("task", ("562034", "656085"))
def test_other_valid_shapes_prove_actual_triangle_section(a, e, am, sk, task):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = condition(a, e, am, sk)
    verify(solution_html(plan(case, ctx)), prepare(ctx, ())[0])


@pytest.mark.parametrize(
    "a,e,am,sk",
    (
        (8, 7, 2, 2),
        (8, 7, 8, 1),
        (8, 7, 2, 7),
        (8, 7, 9, 1),
        (8, 7, 0, 1),
        (8, 7, 2, 0),
        (8, 3, 2, 1),
    ),
)
def test_false_incidence_or_invalid_dimensions_are_refused(a, e, am, sk):
    case = CASES[0]
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = condition(a, e, am, sk)
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
