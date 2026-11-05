"""Check all supported planes and published equalities with independent 3D areas."""

import itertools
from copy import deepcopy

import pytest
import sympy as sp
from box_section_source_cases import CASES, GROUPS, arguments, plan, read, saved_answer
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from test_distance_preparation import verify

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.solids import box_coordinates as c
from solution_runner.pipelines.solids.box_section_model import intersection

RECTANGLES = tuple(
    frozenset(v)
    for v in (
        ("A", "B", "C_1", "D_1"),
        ("A", "D", "B_1", "C_1"),
        ("A", "A_1", "C", "C_1"),
        ("B", "B_1", "D", "D_1"),
        ("A_1", "B_1", "C", "D"),
        ("A_1", "D_1", "B", "C"),
    )
)
TRIPLES = tuple(itertools.combinations(c.VERTICES, 3))
SUPPORTED = tuple(v for v in TRIPLES if any(set(v) <= r for r in RECTANGLES))


def condition(names, *, dimensions="AB=2, AD=3, AA_1=4"):
    return (
        "<p>В прямоугольном параллелепипеде ABCDA_1B_1C_1D_1 известны длины ребер: "
        + dimensions
        + ". Найдите площадь сечения, проходящего через вершины "
        + names[0]
        + ", "
        + names[1]
        + " и "
        + names[2]
        + ".</p>"
    )


def verify_proof(result, model):
    soup = BeautifulSoup(solution_html(result), "html.parser")
    for tag in soup.select("[data-inline-latex]"):
        tag["data-inline-latex"] = tag["data-inline-latex"].replace(
            "S=", "(" + sp.latex(model.answer) + ")="
        )
    verify(str(soup), model)


def independent_area(model):
    p = [
        sp.Matrix([x * sp.sqrt(s) for x, s in zip(c.VERTICES[n], model.squares)])
        for n in model.vertices
    ]
    normal = (p[1] - p[0]).cross(p[3] - p[0])
    assert p[0] + p[2] == p[1] + p[3]
    assert (p[1] - p[0]).dot(p[3] - p[0]) == 0
    return sp.sqrt(normal.dot(normal))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_every_equality_immutable_and_idempotent(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    m = read(case)
    assert ctx == before
    assert (
        sp.simplify(
            ScalarParser(result.answer).parse()
            - ScalarParser(saved_answer(case)).parse()
        )
        == 0
    )
    assert m.answer == independent_area(m)
    verify_proof(result, m)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "source") == section(before, "source")
    assert not BeautifulSoup(section(ctx, "condition")["html"], "html.parser").find(
        "img"
    )
    assert {a["asset_id"] for a in before["normalized_content"]["assets"]} == {
        a["asset_id"] for a in ctx["normalized_content"]["assets"]
    }


@pytest.mark.parametrize("names", TRIPLES)
def test_all_cube_vertex_planes_accept_only_the_six_actual_diagonal_rectangles(names):
    expected = next((r for r in RECTANGLES if set(names) <= r), None)
    if expected:
        assert set(intersection(names)) == expected
    else:
        with pytest.raises(ContentPlanError):
            intersection(names)


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("names", SUPPORTED)
def test_both_parent_methods_prepare_every_supported_plane_and_replay(group, names):
    case = next(c for c in CASES if c["task"] == group)
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = condition(names)
    result = plan(case, ctx)
    m = read({**case, "context": ctx})
    assert m.answer == independent_area(m)
    verify_proof(result, m)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_parent_pins_and_strict_registered_profile(group, field):
    case = next(c for c in CASES if c["task"] == group)
    args = arguments(group)
    changes = (
        {"parent_solution_html": args["parent_solution_html"] + "<p>Другой метод.</p>"}
        if field == "html"
        else {"parent_asset_id": "foreign"}
        if field == "primary"
        else {"parent_solution_assets": ()}
    )
    with pytest.raises(ContentPlanError):
        plan(case, **changes)
    profile = get_group_profile(group)
    handler = get_handler(GROUPS[group]["rule"])
    handler.validate()
    assert (
        profile.source_group_id == GROUPS[group]["group_uuid"]
        and profile.group_order_index == GROUPS[group]["order_index"]
    )
    assert (
        handler.strict_frozen_input
        and handler.requires_frozen_manifest
        and handler.verify_content_readback
    )


@pytest.mark.parametrize(
    "dimensions",
    [
        "AB=0, AD=3, AA_1=4",
        "AB=-2, AD=3, AA_1=4",
        "AB=2, CD=2, AA_1=4",
        "AB=2, AC=3, AA_1=4",
        "AB=2, AD=3",
        "AB=2, AD=3, AA_1=4, BC=3",
    ],
)
def test_incomplete_degenerate_or_other_method_dimensions_fail_closed(dimensions):
    case = CASES[0]
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = condition(
        ("A", "B", "C_1"), dimensions=dimensions
    )
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "bad", [("A", "A", "C"), ("A", "B", "Z"), ("A", "B", "C"), ("A", "B", "D_1")]
)
def test_invalid_unsupported_or_ambiguous_planes_fail_closed(bad):
    if bad == ("A", "B", "D_1"):
        # This plane is supported: test the full condition's extra clause instead.
        html = condition(bad).replace("</p>", " Дополнительно высота равна 7.</p>")
    else:
        html = condition(bad)
    case = CASES[0]
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] = html
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


def test_no_inferred_rectangularity_and_parallel_measurement_aliases():
    case = CASES[0]
    ctx = deepcopy(case["context"])
    current = section(ctx, "condition")
    current["html"] = condition(("A", "B", "C_1"), dimensions="CD=2, BC=3, DD_1=4")
    result = plan(case, ctx)
    m = read({**case, "context": ctx})
    assert m.answer == 10
    verify_proof(result, m)
    current["html"] = current["html"].replace("прямоугольном ", "")
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
