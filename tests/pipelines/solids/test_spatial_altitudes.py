"""Independent native proof equalities, mixed requests and complete-input guards."""

from copy import deepcopy
from dataclasses import replace

import pytest
import sympy as sp
from altitude_geometry_oracle import verify
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from spatial_altitude_source_cases import CASES, GROUPS, plan, read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.distance_figures import prepare
from solution_runner.pipelines.solids.spatial_distance_model import condition_text

EXPECTED = {
    "513097": sp.Rational(60, 13),
    "509977": 30,
    "661267": sp.Rational(120, 17),
    "485988": 1,
    "511329": 2,
    "485992": 1,
    "505153": 3 * sp.sqrt(39) / 4,
    "511397": 2 * sp.sqrt(1239) / 7,
    "505174": sp.sqrt(46) / 4,
    "514474": sp.sqrt(10) / 5,
    "514527": sp.sqrt(2),
    "514534": 3 * sp.sqrt(2) / 2,
    "514653": 2 * sp.sqrt(10) / 5,
}


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_geometry_all_equalities_exact_assets_and_repeat_preparation(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    m = prepare(ctx, ())[0]
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
        4 if case["group"] == "514474" else 2
    )
    assert len(soup.find_all("img")) == len(ctx["normalized_content"]["assets"])
    assert ("Решение векторно-координатным методом" in soup.text) == (
        case["group"] == "514474"
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
        ("513097", "SD = 10", "SD = 11"),
        ("509977", "плоскостью ASB", "плоскостью ASC"),
        ("485988", r"SA=\sqrt{5}", r"SA=\sqrt{6}"),
        ("505174", "пересекаются", "перпендикулярны"),
        ("514474", "прямая AC_1", "прямая A_1C"),
        ("514527", "AK = 2", "AK = 3"),
        ("514534", "середина ребра A_1C_1", "середина ребра B_1C_1"),
        ("514653", "от точки B до", "от точки A до"),
    ),
)
def test_changed_proof_claim_or_impossible_dimensions_are_refused(task, old, new):
    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert old in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, new) + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def scaled(m, factor):
    from solution_runner.pipelines.solids.prism_separation_model import _solve
    from solution_runner.pipelines.solids.spatial_altitude_model import (
        _face,
        _midplane,
        _rectangle,
    )

    givens = [sp.latex(v * factor) for _, v in m.given]
    if m.mode.startswith("rectangular_pyramid"):
        target = "угол" if m.mode.endswith("angle") else "расстояние"
        return _rectangle((*givens, target))
    if m.mode == "square_midplane_distance":
        return _midplane((*givens, m.names[0]))
    if m.mode == "triangle_face_distance":
        return _face((*givens, "AS" if m.names[0] == "perpendicular" else "высоты"))
    a, h, k, l = givens
    triangular = m.mode == "triangle_prism_section_distance"
    positions = (
        ("AK" if triangular else "BK")
        + "="
        + k
        + ", "
        + ("B_1L" if triangular else "C_1L")
        + "="
        + l
    )
    return _solve((a, h, positions, *(() if triangular else m.names)), triangular)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("factor", (sp.Rational(1, 3), sp.Integer(2)))
def test_scaled_dimensions_preserve_math_in_both_parent_methods(case, factor):
    from solution_runner.pipelines.solids.spatial_distance_proofs import render

    original = prepare(case["context"], ())[0]
    m = replace(scaled(original, factor), symbols=original.symbols)
    answer = verify(render(m, {}), m)
    expected = original.answer if m.mode.endswith("angle") else factor * original.answer
    assert sp.simplify(answer - expected) == 0


def test_angle_and_altitude_intersection_children_keep_their_actual_request():
    angle = next(c for c in CASES if c["task"] == "509977")
    assert read(angle["context"]).mode == "rectangular_pyramid_angle"
    assert "∠CSB" in BeautifulSoup(solution_html(plan(angle)), "html.parser").text
    heights = next(c for c in CASES if c["task"] == "505174")
    text = BeautifulSoup(solution_html(plan(heights)), "html.parser").text
    assert "высоты пересекаются" in text and "AS ⟂ BC" not in text
