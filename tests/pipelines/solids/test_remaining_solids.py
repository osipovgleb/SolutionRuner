"""Verify actual volumes, parent methods, source limits and complete asset roles."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from cylinder_formula_oracle import verify as cylinder_proof
from midpoint_source_cases import replay, section, solution_html
from polyhedron_volume_oracle import volume
from remaining_solids_cases import BOUND, GROUPS, PENDING, expected, plan, read
from sphere_formula_oracle import PiParser
from test_polyhedron_preparation import verify_proof as polyhedron_proof

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids.box_coordinates import VERTICES
from solution_runner.pipelines.solids.cylinder_model import (
    read_question as cylinder_question,
)
from solution_runner.pipelines.solids.cylinder_proofs import render as cylinder_render
from solution_runner.pipelines.solids.polyhedron_model import (
    read_question as polyhedron_question,
)
from solution_runner.pipelines.solids.polyhedron_proofs import (
    render as polyhedron_render,
)
from solution_runner.pipelines.solids.polyhedron_svg import edges


@pytest.mark.parametrize("case", BOUND, ids=lambda c: c["task"])
def test_native_answers_all_equalities_immutable_source_and_replay(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    m = read(case)
    assert (
        ctx == before
        and PiParser(result.answer).parse().value
        == PiParser(expected(case)).parse().value
    )
    (cylinder_proof if case["group"] == "27091" else polyhedron_proof)(result, m)
    soup = BeautifulSoup(solution_html(result), "html.parser")
    assert 5 <= len(soup.select("[data-inline-latex]")) <= 9
    assert (
        2
        <= sum(not p.select_one("[data-inline-latex]") for p in soup.find_all("p"))
        <= 4
    )
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "source") == section(before, "source")


@pytest.mark.parametrize(
    "case", [c for c in BOUND if c["group"] != "27091"], ids=lambda c: c["task"]
)
def test_volume_matches_independent_convex_hull(case):
    m = read(case)
    points = [
        tuple(p[i] * sp.sqrt(m.squares[i]) for i in range(3))
        for n, p in VERTICES.items()
        if n in m.solid.vertices
    ]
    assert sp.Rational(volume(points)) == m.answer


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_parent_pins_and_real_catalog_profile(group, field):
    case = next(c for c in BOUND if c["task"] == group)
    overrides = (
        {"parent_solution_html": "<p>Другое решение.</p>"}
        if field == "html"
        else {"parent_asset_id": "foreign"}
        if field == "primary"
        else {"parent_solution_assets": ({"asset_key": "foreign"},)}
    )
    with pytest.raises(ContentPlanError):
        plan(case, **overrides)
    p = get_group_profile(group)
    assert (
        p.source_group_id == GROUPS[group]["group_uuid"]
        and p.group_order_index == GROUPS[group]["order_index"]
    )


@pytest.mark.parametrize("case", PENDING, ids=lambda c: c["task"])
def test_bare_parallelepiped_edges_do_not_imply_rectangular_volume(case):
    with pytest.raises(ContentPlanError, match="oblique"):
        plan(case)
    a, b, c = sp.Integer(2), sp.Integer(3), sp.Integer(5)
    first = sp.Matrix.hstack(
        sp.Matrix((a, 0, 0)), sp.Matrix((0, b, 0)), sp.Matrix((0, 0, c))
    )
    second = sp.Matrix.hstack(
        sp.Matrix((a, 0, 0)), sp.Matrix((0, b, 0)), sp.Matrix((3 * c / 5, 0, 4 * c / 5))
    )
    assert [first[:, i].dot(first[:, i]) for i in range(3)] == [
        second[:, i].dot(second[:, i]) for i in range(3)
    ]
    assert first.det() != second.det() and first.det() > 0 and second.det() > 0


def test_actual_child_prism_does_not_keep_parent_tetrahedron_fraction():
    parent = read(next(c for c in BOUND if c["task"] == "245336"))
    child = read(next(c for c in BOUND if c["task"] == "661012"))
    assert parent.solid.fraction == sp.Rational(1, 6)
    assert (
        child.solid.kind == "prism"
        and child.solid.fraction == sp.Rational(1, 2)
        and child.answer == 120
    )


def test_wrong_tetrahedron_solution_is_replaced_by_the_actual_five_vertex_pyramid():
    case = next(c for c in BOUND if c["task"] == "265013")
    m = read(case)
    handler = get_handler(GROUPS[case["group"]]["rule"])
    specs = handler.diagram_specs(case["context"])
    assert len(specs) == 1
    assert ("A", "C") not in edges(m.solid)
    assert set(m.solid.vertices) == {"A", "B", "C", "D", "D_1"}
    assert "helper-A-C" not in specs[0]["svg_text"]
    result = plan(case)
    assert any(
        t["transformation_target_id"] == "asset:image_2" and t["operation"] == "remove"
        for t in result.transformations
    )


def test_numeric_prism_figure_is_not_reused_for_different_text_dimensions():
    case = next(c for c in BOUND if c["task"] == "661012")
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = section(ctx, "condition")["html"].replace(
        "6", "7"
    )
    handler = get_handler(GROUPS[case["group"]]["rule"])
    assert len(handler.diagram_specs(case["context"])) == 0
    assert len(handler.diagram_specs(ctx)) == 1


@pytest.mark.parametrize("case", BOUND, ids=lambda c: c["task"])
def test_additional_instruction_is_not_discarded(case):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>Умножьте ответ на два.</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "dimensions",
    [(7, 5, 11), (sp.Rational(7, 3), sp.Rational(5, 2), sp.Rational(11, 4))],
)
@pytest.mark.parametrize(
    "names",
    [
        ("A", "B", "C", "D_1"),
        ("A", "B", "D", "A_1", "B_1", "D_1"),
        ("A_1", "B", "C", "C_1", "B_1"),
    ],
)
def test_general_polyhedron_dimensions_and_relative_parent_proof(names, dimensions):
    x, y, z = dimensions
    html = (
        "<p>Найдите объем многогранника, вершинами которого являются точки "
        + ", ".join(names)
        + " прямоугольного параллелепипеда ABCDA_1B_1C_1D_1, у которого AB="
        + sp.latex(x)
        + ", AD="
        + sp.latex(y)
        + ", AA_1="
        + sp.latex(z)
        + ".</p>"
    )
    m = polyhedron_question(html)
    proof = polyhedron_render(m, "", relative=True)
    result = SimpleNamespace(
        transformations=(
            {
                "transformation_target_id": "section:solution:1",
                "value": {"html": proof},
            },
        )
    )
    polyhedron_proof(result, m)
    points = [(p[0] * x, p[1] * y, p[2] * z) for n, p in VERTICES.items() if n in names]
    assert m.answer == sp.Rational(volume(points))


def factor_condition(volume, factor, unit="см<sup>3</sup>", answer_unit=None):
    return (
        "<p>В цилиндрический сосуд налили "
        + volume
        + " "
        + unit
        + " воды. В воду полностью погрузили деталь. При этом уровень жидкости в сосуде увеличился в "
        + factor
        + " раза. Найдите объем детали. Ответ выразите в "
        + (unit if answer_unit is None else answer_unit)
        + ".</p>"
    )


@pytest.mark.parametrize(
    "unit,last",
    [
        ("см<sup>3</sup>", "см<sup>3</sup>"),
        ("куб.\u202fсм", "куб.\u202fсм"),
        ("литров", "литрах"),
    ],
)
@pytest.mark.parametrize("v,k", [("7/3", "5/4"), ("2", "3"), ("10", "1,9")])
def test_factor_displacement_exact_units_and_unseen_data(unit, last, v, k):
    volume = '<span data-inline-latex="' + sp.latex(sp.Rational(v)) + '"></span>'
    factor = (
        '<span data-inline-latex="'
        + sp.latex(sp.Rational(k.replace(",", ".")))
        + '"></span>'
    )
    m = cylinder_question(factor_condition(volume, factor, unit, last))
    expected_value = sp.Rational(v) * (sp.Rational(k.replace(",", ".")) - 1)
    assert m.answer == expected_value
    result = SimpleNamespace(
        answer=sp.latex(m.answer),
        transformations=(
            {
                "transformation_target_id": "section:solution:1",
                "value": {"html": cylinder_render(m)},
            },
        ),
    )
    cylinder_proof(result, m)


@pytest.mark.parametrize("factor", ["1", "0", "0,5", "-2"])
def test_nonincreasing_liquid_factor_is_rejected(factor):
    with pytest.raises(ContentPlanError):
        cylinder_question(factor_condition("10", factor))


def test_mixed_volume_units_and_partial_immersion_are_not_silently_assumed():
    with pytest.raises(ContentPlanError):
        cylinder_question(factor_condition("10", "1,5", "литров", "см<sup>3</sup>"))
    with pytest.raises(ContentPlanError):
        cylinder_question(
            factor_condition("10", "1,5").replace("полностью", "частично")
        )
