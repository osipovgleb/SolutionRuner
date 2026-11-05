"""Independent section geometry, both cube methods and every actual request."""

from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from section_geometry_oracle import verify
from spatial_section_source_cases import CASES, GROUPS, plan, read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.spatial_distance_model import condition_text

EXPECTED = {
    "514603": 12 * sp.sqrt(26) / 13,
    "514617": 16 * sp.sqrt(74) / 37,
    "514631": 36 * sp.sqrt(41) / 41,
    "517200": 2 * sp.sqrt(15) / 7,
    "517238": 5 * sp.sqrt(19) / 18,
    "525727": 5 * sp.sqrt(19) / 18,
    "525746": 2 * sp.sqrt(15) / 7,
    "507596": 10,
    "511447": 2 * sp.sqrt(5),
    "500918": 16 * sp.sqrt(3),
    "508318": 3 * sp.sqrt(3),
    "508391": sp.acos(1 / sp.sqrt(3)),
    "511582": 12 * sp.sqrt(3),
}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_geometry_all_equalities_exact_assets_and_repeat(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    m = read(ctx)
    assert sp.simplify(m.answer - EXPECTED[case["task"]]) == 0
    assert sp.simplify(verify(solution_html(result), m) - m.answer) == 0
    assert ctx == case["context"]
    updated = deepcopy(ctx)
    replay(updated, result.transformations)
    assert not plan(case, updated).transformations
    for key in ("condition", "source", "criteria"):
        assert section(updated, key) == section(ctx, key)
    assert (
        updated["normalized_content"]["assets"] == ctx["normalized_content"]["assets"]
    )
    assert not get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx)
    soup = BeautifulSoup(solution_html(result), "html.parser")
    assert len(soup.select('ol[data-layout="source-subparts"] > li')) == (
        4 if case["group"] == "514603" else 2
    )
    assert len(soup.find_all("img")) == len(ctx["normalized_content"]["assets"])
    assert ("Решение векторно-координатным методом" in soup.text) == (
        case["group"] == "514603"
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "suffix", (" Найдите также объём.", " Докажите дополнительное утверждение.")
)
def test_extra_unread_request_is_refused(case, suffix):
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
        ("514603", "DP = 4", "DP = 5"),
        ("514603", "от точки C до", "от точки C_1 до"),
        ("514617", "Плоскость A_1PQ", "Плоскость APQ"),
        ("517200", "равны 4", "равны 5"),
        ("517200", "SF = BE = 3", "SF = 2, BE = 3"),
        ("507596", "равен 36°", "равен 40°"),
        ("507596", "AM=AB", "AM=AS"),
        ("508318", "середина бокового ребра AP", "середина бокового ребра BP"),
        ("508391", "параллельной плоскости BCP", "параллельной плоскости ACD"),
    ),
)
def test_false_claim_or_unsupported_construction_is_refused(task, old, new):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert old in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, new) + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def scaled(m, factor):
    from solution_runner.pipelines.solids.cube_plane_section_model import _solve
    from solution_runner.pipelines.solids.spatial_section_model import (
        _bisector,
        _parallel,
        _trapezoid,
    )

    givens = [sp.latex(v * factor) for _, v in m.given]
    if m.mode.startswith("cube_"):
        a, p, b = givens
        vertical = m.mode == "cube_vertical_plane_distance"
        apex, target = ("A_1", "C_1") if vertical else ("A", "C")
        return _solve(("DD_1" if vertical else "CD", a, p, b, apex, target, apex))
    if m.mode == "pyramid_parallel_section_height":
        return _parallel(givens)
    if m.mode.startswith("triangle_bisector_"):
        area = m.mode.endswith("area")
        given = m.given[0][1] * factor ** (1 if area else 2)
        return _bisector(("36", sp.latex(given)), area)
    return _trapezoid(
        (givens[0], "прямым PB и BC", "угол" if m.mode.endswith("angle") else "площадь")
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("factor", (sp.Rational(1, 3), sp.Integer(2)))
def test_scaled_geometry_preserves_lengths_areas_angles_and_both_cube_methods(
    case, factor
):
    from solution_runner.pipelines.solids.spatial_distance_proofs import render

    original = read(case["context"])
    m = scaled(original, factor)
    power = 0 if m.mode.endswith("angle") else 2 if m.mode.endswith("area") else 1
    assert sp.simplify(verify(render(m, {}), m) - factor**power * original.answer) == 0


@pytest.mark.parametrize("a,d,e,t", (("3", "7", "4", "3"), ("4", "9", "5", "4")))
def test_parallel_section_does_not_assume_base_edge_equals_lateral_edge(a, d, e, t):
    from solution_runner.pipelines.solids.spatial_section_model import _parallel
    from solution_runner.pipelines.solids.spatial_section_proofs import render

    m = _parallel((a, d, e, t))
    assert m.q["BM"] != m.q["t"]
    assert sp.simplify(verify(render(m, {}), m) - m.answer) == 0


def test_area_and_angle_children_are_not_replaced_with_parent_request():
    area = next(c for c in CASES if c["task"] == "500918")
    assert read(area["context"]).mode == "triangle_bisector_section_area"
    angle = next(c for c in CASES if c["task"] == "508391")
    assert read(angle["context"]).mode == "pyramid_parallel_section_angle"
    soup = BeautifulSoup(solution_html(plan(angle)), "html.parser")
    assert len(soup.find_all("img")) == 1 and "площадь" not in soup.text.lower()
    assert r"\arccos" in plan(angle).answer
