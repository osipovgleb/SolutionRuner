"""Verify all eight midpoint sections and every equality against independent 3D coordinates."""

import itertools
import re
from copy import deepcopy

import pytest
import sympy as sp
from box_midpoint_source_cases import CASES, arguments, plan, read, saved_answer
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.logarithm_parser import LogarithmParser
from solution_runner.pipelines.equations.power_arithmetic import ScalarParser
from solution_runner.pipelines.solids import box_coordinates as c

RULE = "solid-box-midpoint-section"
TOP_EDGES = tuple(
    (a, b)
    for a, b in itertools.combinations(c.VERTICES, 2)
    if a.endswith("_1") and b.endswith("_1") and len(c.axes(a + b)) == 1
)
CONFIGURATIONS = tuple(
    (a, b, lower)
    for a, b in TOP_EDGES
    for lower in "ABCD"
    if lower + "_1" not in (a, b)
)


def condition(a, b, lower, measurements="ребро AB=2, ребро AD=3, ребро AA_1=4"):
    return (
        "<p>В прямоугольном параллелепипеде ABCDA_1B_1C_1D_1 "
        + measurements
        + ". Точка K — середина ребра "
        + lower
        + lower
        + "_1. Найдите площадь сечения, проходящего через точки "
        + a
        + ", "
        + b
        + " и K.</p>"
    )


def independent_points(m):
    # K is reconstructed from the given edge, K1 from translation by the top edge.
    top_a, top_b = m.vertices[:2]
    u, v = c.endpoints(m.midpoint_edge)
    mid = (sp.Matrix(c.VERTICES[u]) + sp.Matrix(c.VERTICES[v])) / 2
    step = sp.Matrix(c.VERTICES[top_b]) - sp.Matrix(c.VERTICES[top_a])
    other = mid + step if all(0 <= x <= 1 for x in mid + step) else mid - step
    raw = {**{n: sp.Matrix(p) for n, p in c.VERTICES.items()}, "K": mid, "K_1": other}
    return {
        n: sp.Matrix([x * sp.sqrt(s) for x, s in zip(p, m.squares)])
        for n, p in raw.items()
    }


def verify_proof(result, m):
    points = independent_points(m)
    p, q, r, s = [points[n] for n in m.vertices]
    assert p + r == q + s and (q - p).dot(s - p) == 0
    normal = (q - p).cross(s - p)
    area = sp.sqrt(normal.dot(normal))
    assert sp.simplify(m.answer - area) == 0
    values = {
        a + b: sp.sqrt((points[a] - points[b]).dot(points[a] - points[b]))
        for a, b in itertools.permutations(points, 2)
    }
    values["S"] = area
    for node in BeautifulSoup(solution_html(result), "html.parser").select(
        "[data-inline-latex]"
    ):
        f = node["data-inline-latex"]
        for name, amount in sorted(values.items(), key=lambda p: -len(p[0])):
            f = re.sub(
                r"(?<![A-Za-z_])" + re.escape(name) + r"(?![A-Za-z_])",
                lambda _, v=amount: "(" + sp.latex(v) + ")",
                f,
            )
        expressions = [LogarithmParser(part).parse().value for part in f.split("=")]
        assert len(expressions) > 1 and all(
            sp.simplify(v - expressions[0]) == 0 for v in expressions
        ), f


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_answers_formulas_cyclic_boundary_source_ids_and_idempotence(case):
    ctx = deepcopy(case["context"])
    section(ctx, "answer")["html"] = "<p>999</p>"
    before = deepcopy(ctx)
    result = plan(case, ctx)
    m = read(case)
    assert (
        ctx == before
        and sp.simplify(
            ScalarParser(result.answer).parse()
            - ScalarParser(saved_answer(case)).parse()
        )
        == 0
    )
    verify_proof(result, m)
    assert get_handler(RULE).diagram_specs(ctx) == ()
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "source") == section(before, "source")
    assert {a["asset_id"] for a in before["normalized_content"]["assets"]} <= {
        a["asset_id"] for a in ctx["normalized_content"]["assets"]
    }
    assert section(ctx, "condition") == section(before, "condition")
    if case["task"] == "505383":
        assert m.vertices == ("A_1", "B_1", "K", "K_1")


@pytest.mark.parametrize("configuration", CONFIGURATIONS)
@pytest.mark.parametrize("case", CASES[:2], ids=lambda c: c["task"])
def test_every_top_edge_midpoint_configuration_with_or_without_condition_picture(
    configuration, case
):
    ctx = deepcopy(case["context"])
    old = BeautifulSoup(section(ctx, "condition")["html"], "html.parser").find("img")
    html = condition(*configuration)
    section(ctx, "condition")["html"] = (
        html.replace("<p>", "<p>" + str(old), 1) if old else html
    )
    result = plan(case, ctx)
    m = read({**case, "context": ctx})
    verify_proof(result, m)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()


@pytest.mark.parametrize(
    "a,b,lower",
    [(a, b, lower) for a, b in TOP_EDGES for lower in "ABCD" if lower + "_1" in (a, b)],
)
def test_midpoint_on_same_face_is_not_a_corner_of_the_parent_section(a, b, lower):
    ctx = deepcopy(CASES[-1]["context"])
    section(ctx, "condition")["html"] = condition(a, b, lower)
    with pytest.raises(ContentPlanError):
        plan(CASES[-1], ctx)


@pytest.mark.parametrize(
    "mutation",
    [
        "negative",
        "zero",
        "redundant",
        "diagonal",
        "horizontal_midpoint",
        "repeated_top",
        "bottom",
        "instruction",
        "not_rectangular",
    ],
)
def test_unknown_or_degenerate_conditions_fail_closed(mutation):
    html = condition("A_1", "D_1", "B")
    replacements = {
        "negative": ("AB=2", "AB=-2"),
        "zero": ("AD=3", "AD=0"),
        "redundant": ("AD=3", "CD=2"),
        "diagonal": ("AD=3", "AC=3"),
        "horizontal_midpoint": ("середина ребра BB_1", "середина ребра AB"),
        "repeated_top": ("A_1, D_1", "A_1, A_1"),
        "bottom": ("A_1, D_1", "A, D_1"),
        "not_rectangular": ("прямоугольном ", ""),
    }
    if mutation == "instruction":
        html = html.replace("</p>", " Округлите до сотых.</p>")
    else:
        html = html.replace(*replacements[mutation])
    ctx = deepcopy(CASES[-1]["context"])
    section(ctx, "condition")["html"] = html
    with pytest.raises(ContentPlanError):
        plan(CASES[-1], ctx)


@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_complete_parent_pins_and_strict_profile(field):
    args = arguments("315131")
    override = (
        {"parent_solution_html": args["parent_solution_html"] + "<p>Другой метод.</p>"}
        if field == "html"
        else {"parent_asset_id": "foreign"}
        if field == "primary"
        else {"parent_solution_assets": ()}
    )
    with pytest.raises(ContentPlanError):
        plan(CASES[0], **override)
    profile = get_group_profile("315131")
    handler = get_handler(RULE)
    handler.validate()
    assert (
        profile.group_order_index == 25
        and profile.source_group_id == "0f90bb18-03e8-4ac5-9467-c9c1c94cf7a5"
    )
    assert (
        handler.requires_frozen_manifest
        and handler.strict_frozen_input
        and handler.verify_content_readback
    )
