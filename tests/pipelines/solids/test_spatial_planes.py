"""Native proofs, independently calculated answers, and complete request guards."""

from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from plane_geometry_oracle import verify
from plane_source_cases import CASES, GROUPS, plan, read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.spatial_distance_model import condition_text

EXPECTED = {
    "507794": 10 * sp.sqrt(2),
    "511494": 8 * sp.sqrt(2),
    "507800": 6 * sp.sqrt(6),
    "504241": 5,
    "511386": 4 * sp.sqrt(3) / 3,
    "504262": 10,
    "484575": sp.sqrt(91) / 2,
    "484576": sp.sqrt(21),
    "485941": 2 * sp.sqrt(7),
    "526290": sp.sqrt(3) / 2,
    "526325": sp.sqrt(3) / 4,
    "526529": sp.sqrt(2) / 6,
    "527235": sp.acos(31 * sp.sqrt(10) / 140),
}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_geometry_every_displayed_equality_and_repeat_preparation(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    m = read(ctx)
    # Figure metadata determines auxiliary letters and the native proof variant.
    from solution_runner.pipelines.solids.distance_figures import prepare

    handler = get_handler(GROUPS[case["group"]]["rule"])
    specs = handler.diagram_specs(ctx)
    generated = tuple(
        {
            "asset_key": s["asset_key"],
            "sha256": s["sha256"],
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in specs
    )
    m = prepare(ctx, generated)[0]
    assert sp.simplify(m.answer - EXPECTED[case["task"]]) == 0
    assert sp.simplify(verify(solution_html(result), m) - m.answer) == 0
    assert ctx == case["context"]
    updated = deepcopy(ctx)
    replay(updated, result.transformations)
    assert not plan(case, updated).transformations
    for key in ("condition", "source", "criteria"):
        assert section(updated, key) == section(ctx, key)
    soup = BeautifulSoup(solution_html(result), "html.parser")
    assert len(soup.select('ol[data-layout="source-subparts"] > li')) == 2
    assert len(soup.find_all("img")) == (
        2 if case["group"] == "484575" or case["task"] == "526529" else 1
    )
    assert bool(specs) == (case["task"] in {"526290", "526325"})
    if case["group"] == "507794":
        assert "Примечание" in soup.text and "x^{4}" in solution_html(result)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "suffix", (" Найдите также объём.", " Докажите дополнительное утверждение.")
)
def test_extra_request_is_refused(case, suffix):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>" + suffix + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_parent_method_pin_drift_is_refused(case):
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_html="changed")


@pytest.mark.parametrize(
    "task,old,new",
    (
        ("507794", "угол A равен 30°", "угол A равен 75°"),
        ("507800", r"\angle NM_1E=30°", r"\angle NM_1E=45°"),
        ("504241", "ACL и MDB", "ACL и MAB"),
        ("484575", "CD_1E_1 и AEE_1", "CD_1E_1 и ABB_1"),
        ("526290", "считая от вершины S", "считая от вершины A"),
        ("526325", "1: 2, считая", "1: 3, считая"),
        ("527235", "параллельна прямой BC", "параллельна прямой AB"),
    ),
)
def test_false_claim_or_unsupported_geometry_is_refused(task, old, new):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert old in raw, raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, new) + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["group"] == "507794"], ids=lambda c: c["task"]
)
def test_cosine_law_polynomial_identity_before_substituting_the_height(case):
    m = read(case["context"])
    t = sp.Symbol("t")
    q = m.q
    squared_cosine_law = (t + q["BE"] ** 2) ** 2 - q["cos_beta"] ** 2 * (
        t + q["BC"] ** 2
    ) * (t + q["BE"] ** 2)
    factored = q["sin_beta"] ** 2 * (t + q["BE"] ** 2) * (t - q["H"] ** 2)
    assert sp.simplify(squared_cosine_law - factored) == 0


def test_angle_child_keeps_angle_request_and_does_not_restore_distance_diagram():
    case = next(c for c in CASES if c["task"] == "527235")
    result = plan(case)
    assert r"\arccos" in result.answer
    assert "расстояни" not in BeautifulSoup(solution_html(result), "html.parser").text
    assert not get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(case["context"])


@pytest.mark.parametrize(
    "a,e,p,q,angle",
    (
        ("5", "3", "4", "1", False),
        ("6", "5", "1", "3", False),
        ("6", r"3\sqrt{2}", "2", "5", True),
        ("9", "6", "2", "7", True),
    ),
)
def test_ratio_method_handles_other_ratios_right_and_obtuse_section_angles(
    a, e, p, q, angle
):
    from solution_runner.pipelines.solids.spatial_plane_model import _ratio
    from solution_runner.pipelines.solids.spatial_plane_proofs import render

    groups = (a, e, p, q) + (() if angle else ("SB", p, q, "S"))
    m = _ratio(groups, angle)
    html = render(m, {})
    assert sp.simplify(verify(html, m) - m.answer) == 0


@pytest.mark.parametrize("tangent", ("2", "3", "0", "-1"))
def test_impossible_square_pyramid_tangent_is_refused(tangent):
    from solution_runner.pipelines.solids.spatial_plane_model import _tangent

    with pytest.raises(ContentPlanError):
        _tangent(("5", tangent))
