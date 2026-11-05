"""Both parent methods, noncentroid plain sections and strict full requests."""

import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from regular_triangle_cut_geometry_oracle import verify
from regular_triangle_cut_source_cases import CASES, plan
from test_pyramid_midsections_lifecycle import without_figures

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.distance_figures import selection
from solution_runner.pipelines.solids.spatial_distance_model import condition_text

EXPECTED = {
    "505417": 4 * sp.sqrt(210) / 5,
    "511405": sp.sqrt(210) / 5,
    "505423": 2 * sp.sqrt(30),
    "505450": 4 * sp.sqrt(33),
}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_every_equality_methods_assets_and_repeat(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    m = selection(ctx)[0]
    assert sp.simplify(m.answer - EXPECTED[case["task"]]) == 0
    assert sp.simplify(verify(solution_html(result), m) - m.answer) == 0
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations
    for key in ("condition", "source", "criteria"):
        assert section(ctx, key) == section(case["context"], key)
    if case["task"] == "505450":
        assert len(ctx["normalized_content"]["assets"]) == 1
        assert (
            ctx["normalized_content"]["assets"][0]["asset_key"]
            == "box_distance_solution"
        )
    else:
        assert (
            ctx["normalized_content"]["assets"]
            == case["context"]["normalized_content"]["assets"]
        )
    soup = BeautifulSoup(solution_html(result), "html.parser")
    assert len(soup.find_all("img")) == (2 if case["task"] == "505417" else 1)
    assert len(soup.select('ol[data-layout="source-subparts"] > li')) == (
        0 if case["task"] == "505450" else 2
    )
    assert (
        solution_html(result).index("LK=")
        < solution_html(result).index("другое решение")
        < solution_html(result).index("LE^2=")
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_missing_figures_restore_one_complete_scene_and_both_methods(case):
    ctx = without_figures(case)
    result = plan(case, ctx)
    verify(solution_html(result), selection(ctx)[0])
    replay(ctx, result.transformations)
    assert len(ctx["normalized_content"]["assets"]) == 1
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("factor", (sp.Rational(3, 2), 3))
def test_scaling_recomputes_every_projection_and_cosine_line(case, factor):
    ctx = deepcopy(case["context"])
    m = selection(ctx)[0]
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert len(re.findall(r"\d+", raw)) == 3
    raw = re.sub(r"\d+", lambda match: sp.latex(sp.Integer(match[0]) * factor), raw)
    section(ctx, "condition")["html"] = "<p>" + raw + "</p>"
    result = plan(case, ctx)
    new = selection(ctx)[0]
    assert sp.simplify(new.answer - factor**2 * m.answer) == 0
    verify(solution_html(result), new)
    replay(ctx, result.transformations)
    assert not plan(case, ctx).transformations


def condition(a, e, u, claim=False):
    return (
        "<p>В правильной треугольной пирамиде MABC с основанием ABC стороны основания равны "
        + sp.latex(a)
        + ", а боковые ребра "
        + sp.latex(e)
        + ". На ребре AC находится точка D, на ребре AB находится точка E, а на ребре AM — точка L. Известно, что CD = BE = LM = "
        + sp.latex(u)
        + ". "
        + (
            "Докажите, что плоскость EDL содержит центр основания пирамиды. "
            if claim
            else ""
        )
        + "Найдите площадь сечения пирамиды этой плоскостью.</p>"
    )


@pytest.mark.parametrize("a,e,u", ((8, 20, 3), (8, 12, 3), (8, 15, 5), (6, 8, 2)))
def test_other_plain_cuts_distinguish_the_midpoint_projection_and_center(a, e, u):
    case = CASES[-1]
    ctx = deepcopy(case["context"])
    ctx = without_figures({**case, "context": ctx})
    section(ctx, "condition")["html"] = condition(a, e, u)
    result = plan(case, ctx)
    m = selection(ctx)[0]
    verify(solution_html(result), m)
    if a == 6:
        assert m.symbols["section_foot"] == "O"
    else:
        assert m.symbols["section_foot"] == "H"


@pytest.mark.parametrize(
    "a,e,u,claim",
    (
        (8, 16, 4, True),
        (8, 16, 0, False),
        (8, 16, 8, False),
        (8, 4, 4, False),
        (10, 5, 1, False),
    ),
)
def test_false_centroid_or_invalid_edges_and_solid_are_refused(a, e, u, claim):
    case = CASES[-1]
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = condition(a, e, u, claim)
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_extra_request_and_parent_method_drift_are_refused(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Найдите также объём.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_html="changed")


@pytest.mark.parametrize("field", ("asset_key", "sha256", "source_asset_id", "url"))
def test_generated_bindings_cannot_change_the_reviewed_svg_or_identity(field):
    from regular_triangle_cut_source_cases import GROUPS

    from solution_runner.pipelines.core.handler_registry import get_handler

    case = CASES[-1]
    spec = get_handler(GROUPS["505417"]["rule"]).diagram_specs(case["context"])[0]
    item = {
        "asset_key": spec["asset_key"],
        "sha256": spec["sha256"],
        "source_asset_id": "preview-" + spec["sha256"][:16],
        "url": "/assets/preview-" + spec["sha256"][:16],
    }
    item[field] = "foreign"
    with pytest.raises(ContentPlanError):
        plan(case, generated_solution_assets=(item,))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_unreviewed_native_source_is_not_silently_replaced(case):
    ctx = deepcopy(case["context"])
    asset = ctx["normalized_content"]["assets"][0]
    old = asset["asset_id"]
    uid = "00000000-0000-4000-8000-000000000001"
    asset["asset_id"], asset["url"] = uid, "/assets/" + uid
    section(ctx, "solution")["html"] = section(ctx, "solution")["html"].replace(
        old, uid
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
