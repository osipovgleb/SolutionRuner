"""Check actual angles and each proof equality against independent 3D vectors."""

import itertools
import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from test_distance_preparation import verify
from vertex_angle_source_cases import CASES, GROUPS, arguments, plan, read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.solids import box_coordinates as c
from solution_runner.pipelines.solids.box_vertex_angle_model import read_question


def angle(requested, squares):
    a, b, d = re.findall(c.VERTEX, requested)
    points = {
        n: sp.Matrix([x * sp.sqrt(s) for x, s in zip(p, squares)])
        for n, p in c.VERTICES.items()
    }
    u, v = points[a] - points[b], points[d] - points[b]
    return sp.simplify(180 * sp.acos(u.dot(v) / sp.sqrt(u.dot(u) * v.dot(v))) / sp.pi)


def verify_proof(result, m):
    soup = BeautifulSoup(solution_html(result), "html.parser")
    for tag in soup.select("[data-inline-latex]"):
        formula = tag["data-inline-latex"].replace(r"^{\circ}", "")
        formula = re.sub(
            r"\\angle\s+((?:" + c.VERTEX + r"){3})",
            lambda match: "(" + sp.latex(angle(match[1], m.squares)) + ")",
            formula,
        )
        tag["data-inline-latex"] = formula
    verify(str(soup), m)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_angles_equalities_source_roles_and_empty_replay(case):
    ctx = deepcopy(case["context"])
    before = deepcopy(ctx)
    result = plan(case, ctx)
    m = read(case)
    assert ctx == before and m.answer == angle(m.requested, m.squares) == 45
    assert result.answer == "45"
    verify_proof(result, m)
    if case["group"] == "245361":
        first = BeautifulSoup(solution_html(result), "html.parser").find("p")
        assert first.find("img") is not None and not first.get_text(strip=True)
    replay(ctx, result.transformations)
    assert plan(case, ctx).transformations == ()
    assert section(ctx, "source") == section(before, "source")
    assets = ctx["normalized_content"]["assets"]
    assert len(assets) == (2 if case["group"] == "245361" else 1)
    if case["task"] not in {"271575"}:
        assert {a["asset_key"]: a["asset_id"] for a in assets} == {
            a["asset_key"]: a["asset_id"]
            for a in before["normalized_content"]["assets"]
        }
    section(ctx, "answer")["html"] = "<p>999</p>"
    assert plan(case, ctx).answer == "45"


def condition(requested, given):
    return (
        "<p>Найдите угол "
        + requested
        + " прямоугольного параллелепипеда, для которого "
        + given
        + ". Ответ дайте в градусах.</p>"
    )


RIGHT = []
for a, b, d in itertools.permutations(c.VERTICES, 3):
    ua = tuple(x - y for x, y in zip(c.VERTICES[a], c.VERTICES[b]))
    ud = tuple(x - y for x, y in zip(c.VERTICES[d], c.VERTICES[b]))
    if sum(x * y for x, y in zip(ua, ud)) != 0:
        continue
    squares = [sp.Integer(2)] * 3
    aa = sum(x * x * s for x, s in zip(ua, squares))
    dd = sum(x * x * s for x, s in zip(ud, squares))
    if aa != dd:
        mask_a = set(c.axes(a + b))
        mask_d = set(c.axes(b + d))
        if len(mask_a) == 1:
            squares[next(iter(mask_a))] = 4
        else:
            squares[next(iter(mask_d))] = 4
    RIGHT.append((b + a + d, tuple(squares)))


@pytest.mark.parametrize("requested,squares", RIGHT)
def test_all_right_triangle_orientations_prove_angle_instead_of_assuming_it(
    requested, squares
):
    given = ", ".join(
        n + "=" + sp.latex(sp.sqrt(s)) for n, s in zip(("AB", "AD", "AA_1"), squares)
    )
    m = read_question(condition(requested, given))
    assert m.answer == angle(requested, squares) == 45
    assert m.right == re.findall(c.VERTEX, requested)[0]


@pytest.mark.parametrize(
    "requested,given",
    [
        ("ABD_1", "AB=6, AD=4, AA_1=3"),
        ("BAD_1", "AB=5, AD=4, AA_1=3"),
        ("ABC", "AB=2, AD=3, AA_1=4"),
        ("AAA_1", "AB=2, AD=3, AA_1=4"),
        ("ABD_1", "AB=0, AD=4, AA_1=3"),
        ("ABD_1", "AB=-5, AD=4, AA_1=3"),
        ("ABD_1", "AB=5, AD=4"),
        ("ABD_1", "AB=5, AD=4, AA_1=3, BC=4"),
        ("ABD_1", "AC=5, AD=4, AA_1=3"),
    ],
)
def test_different_or_impossible_parent_method_rejected(requested, given):
    with pytest.raises(ContentPlanError):
        read_question(condition(requested, given))


@pytest.mark.parametrize("group", GROUPS)
@pytest.mark.parametrize("field", ["html", "primary", "assets"])
def test_parent_method_is_fully_pinned(group, field):
    case = next(c for c in CASES if c["task"] == group)
    args = arguments(group)
    changes = (
        {"parent_solution_html": args["parent_solution_html"] + "<p>Другой метод</p>"}
        if field == "html"
        else {"parent_asset_id": "foreign"}
        if field == "primary"
        else {"parent_solution_assets": ({"asset_key": "image_9"},)}
    )
    with pytest.raises(ContentPlanError):
        plan(case, **changes)
    handler = get_handler(GROUPS[group]["rule"])
    handler.validate()
    assert (
        handler.requires_frozen_manifest
        and handler.verify_content_readback
        and handler.strict_frozen_input
    )
