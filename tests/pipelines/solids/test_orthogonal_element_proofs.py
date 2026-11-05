"""Check every native proof, unseen dimensions and false geometric witnesses."""

from dataclasses import replace

import pytest
import sympy as sp
from orthogonal_element_cases import BOUND, PENDING, model
from orthogonal_element_oracle import verify

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.orthogonal_element_geometry import answer, frame
from solution_runner.pipelines.solids.orthogonal_element_model import projection, read
from solution_runner.pipelines.solids.orthogonal_element_proofs import render
from solution_runner.pipelines.solids.orthogonal_element_sources import DATA


@pytest.mark.parametrize("case", BOUND, ids=lambda c: c["task"])
def test_every_published_equality_agrees_with_the_actual_native_geometry(case):
    m = model(case)
    verify(m, render(m))


@pytest.mark.parametrize("case", BOUND, ids=lambda c: c["task"])
def test_proof_formulas_work_with_unseen_rational_lengths(case):
    m = model(case)
    factor = sp.Rational(7, 3)
    given = {k: str(factor * sp.Rational(v)) for k, v in m.given.items()}
    vertices = frame(m.kind, given)
    if "K" in m.points:
        vertices["K"] = factor * m.points["K"]
    power = {"distance": 1, "distance_squared": 2, "angle": 0, "tangent": 0}[m.mode]
    scaled = replace(m, given=given, points=vertices, value=m.value * factor**power)
    verify(scaled, render(scaled))


@pytest.mark.parametrize(
    "case", [c for c in BOUND if c["mode"] != "angle"], ids=lambda c: c["task"]
)
def test_independent_dimension_changes_do_not_reuse_equal_number_shortcuts(case):
    m = model(case)
    review = DATA["proofs"][
        case["source"] + ":" + case["mode"] + ":" + case["requested"]
    ]
    for dimension in m.given:
        given = {
            **m.given,
            dimension: str(sp.Rational(m.given[dimension]) * sp.Rational(101, 100)),
        }
        vertices = frame(m.kind, given)
        amount = answer(vertices, m.mode, m.requested)
        if "K" in m.points:
            vertices["K"] = projection(
                vertices, review.get("projection_names", m.names), review["projection"]
            )
        varied = replace(m, given=given, points=vertices, value=amount)
        verify(varied, render(varied))


@pytest.mark.parametrize("case", BOUND, ids=lambda c: c["task"])
def test_another_parent_method_is_never_silently_selected(case):
    with pytest.raises(ContentPlanError, match="parent construction"):
        read(case["source"], case["mode"], case["requested"], "unreviewed")


@pytest.mark.parametrize("case", PENDING, ids=lambda c: c["task"])
def test_incomplete_source_is_rejected_before_any_solution_is_built(case):
    with pytest.raises(ContentPlanError, match="PNG"):
        read(case["source"], case["mode"], case["requested"], "space_distance")


def test_equal_numeric_answers_do_not_authorize_another_triangle():
    case = BOUND[0]
    with pytest.raises(ContentPlanError, match="construction"):
        read(case["source"], "distance", "AD_2", "space_distance")


@pytest.mark.parametrize("method", ["equilateral", "isosceles"])
def test_changed_geometry_cannot_keep_a_fixed_parent_degree_answer(method):
    m = next(model(c) for c in BOUND if model(c).method == method)
    points = {
        n: sp.ImmutableMatrix((2 * p[0], p[1], p[2])) for n, p in m.points.items()
    }
    with pytest.raises(ContentPlanError):
        render(replace(m, points=points))


def test_formula_verifier_detects_an_incorrect_intermediate_value():
    m = model(BOUND[0])
    html = render(m).replace("=4+5", "=999+5")
    assert html != render(m)
    with pytest.raises(AssertionError):
        verify(m, html)


def test_source_bindings_preserve_every_available_native_solution_picture():
    for c in BOUND:
        review = DATA["proofs"][c["source"] + ":" + c["mode"] + ":" + c["requested"]]
        source = next(
            (
                a["asset_id"]
                for a in c["context"]["normalized_content"]["assets"]
                if a["asset_key"] == "image_2"
            ),
            None,
        )
        assert review["solution_source"] == source
