"""Independently verify distance geometry, each proof equality and native figures."""

import itertools
import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import replay, section, solution_html
from spatial_distance_cases import CASES, GROUPS, plan, read

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.solids.box_coordinates import VERTICES
from solution_runner.pipelines.solids.spatial_distance_model import read_question

EXPECTED = (
    sp.sqrt(15) / 5,
    sp.sqrt(5) / 5,
    2 * sp.sqrt(5) / 5,
    12,
    sp.Rational(60, 13),
    sp.Rational(120, 17),
)


def geometry(m):
    if m.mode == "pyramid_skew_midpoint":
        a, h = m.q["a"], m.q["H"]
        points = {
            "A": sp.Matrix([-a / 2, -a / 2, 0]),
            "B": sp.Matrix([a / 2, -a / 2, 0]),
            "C": sp.Matrix([a / 2, a / 2, 0]),
            "D": sp.Matrix([-a / 2, a / 2, 0]),
            "S": sp.Matrix([0, 0, h]),
            "H": sp.zeros(3, 1),
            "N": sp.Matrix([0, -a / 2, 0]),
            "M": sp.Matrix([0, a / 2, 0]),
        }
        points["T"] = (points["S"] + points["M"]) / 2
        u, v = points["T"] - points["N"], points["C"] - points["S"]
        distance = abs((points["S"] - points["N"]).dot(u.cross(v))) / u.cross(v).norm()
        p, q, r = points["T"], points["S"], points["C"]
        normal = (points["C"] - points["S"]).cross(points["D"] - points["S"])
        assert sp.simplify(u.cross(normal).norm()) == 0
    else:
        points = {
            n: sp.Matrix([sp.sqrt(s) * x for s, x in zip(m.squares, p, strict=True)])
            for n, p in VERTICES.items()
        }
        p, q, r = (points[n] for n in m.names)
        distance = (p - q).cross(r - q).norm() / (r - q).norm()
        assert distance < (p - q).norm()
    direction = r - q
    points["E"] = q + (p - q).dot(direction) / direction.dot(direction) * direction
    assert sp.simplify((p - points["E"]).dot(direction)) == 0
    return points, sp.simplify(distance)


def verify(html, m):
    points, independent = geometry(m)
    substitutions = {
        a + b: sp.simplify((p - q).norm())
        for a, p in points.items()
        for b, q in points.items()
        if a != b
    }
    for span in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = span["data-inline-latex"]
        for name, number in sorted(substitutions.items(), key=lambda x: -len(x[0])):
            formula = re.sub(
                r"(?<![A-Za-z_])" + re.escape(name) + r"(?![A-Za-z_])",
                lambda _, v=number: "(" + sp.latex(v) + ")",
                formula,
            )
        values = [TrigonometricParser(p).parse().value for p in formula.split("=")]
        assert len(values) > 1, formula
        assert all(sp.simplify(v - values[0]) == 0 for v in values), formula
    return independent


@pytest.mark.parametrize(
    "case,expected", tuple(zip(CASES, EXPECTED)), ids=[c["task"] for c in CASES]
)
def test_native_proofs_geometry_replay_and_exact_roles(case, expected):
    original = deepcopy(case["context"])
    m = read(original)
    result = plan(case)
    assert sp.simplify(m.answer - expected) == 0
    html = solution_html(result)
    assert verify(html, m) == expected
    soup = BeautifulSoup(html, "html.parser")
    assert len(soup.select('ol[data-layout="source-subparts"] > li')) == 2
    assert [
        (i["data-asset-key"], i["data-asset-id"]) for i in soup.find_all("img")
    ] == [
        (a["asset_key"], a["asset_id"])
        for a in original["normalized_content"]["assets"]
    ]
    assert not get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(original)
    replay(original, result.transformations)
    assert not plan(case, original).transformations
    for key in ("condition", "source", "criteria"):
        assert section(original, key) == section(case["context"], key)
    assert (
        original["normalized_content"]["assets"]
        == case["context"]["normalized_content"]["assets"]
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("suffix", (" Найдите также объём.", " Уберите пункт а)."))
def test_extra_unread_request_refused(case, suffix):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>" + suffix + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize("value", ("1", "2", "4", "0", "-3"))
def test_false_midpoint_or_impossible_pyramid_is_refused(value):
    ctx = deepcopy(CASES[0]["context"])
    sec = section(ctx, "condition")
    sec["html"] = (
        sec["html"]
        .replace("равна\u202f3.", "равна\u202f" + value + ".")
        .replace("равна\u202f3", "равна\u202f" + value)
    )
    # The actual source uses a narrow nonbreaking separator.
    assert sec["html"] != section(CASES[0]["context"], "condition")["html"]
    with pytest.raises((ContentPlanError, ValueError)):
        plan(CASES[0], ctx)


@pytest.mark.parametrize(
    "scale", (sp.Rational(1, 3), sp.Rational(7, 2), sp.Integer(11))
)
def test_scaled_pyramid_proof_and_distance(scale):
    ctx = deepcopy(CASES[2]["context"])
    sec = section(ctx, "condition")
    text = f"В правильной четырехугольной пирамиде SABCD сторона основания AB = {sp.latex(4 * scale)}, а боковое ребро SA={sp.latex(2 * sp.sqrt(5) * scale)}. Точки M и N — середины ребер CD и AB соответственно. Точка N — вершина пирамиды NSCD, NT — ее высота. Докажите, что точка T делит SM пополам. Найдите расстояние между прямыми NT и SC."
    for formula in (sp.latex(4 * scale), sp.latex(2 * sp.sqrt(5) * scale)):
        text = text.replace(
            formula, '<span data-inline-latex="' + formula + '"></span>', 1
        )
    sec["html"] = "<p>" + text + "</p>"
    m = read(ctx)
    result = plan(CASES[2], ctx)
    assert (
        sp.simplify(verify(solution_html(result), m) - scale * 2 * sp.sqrt(5) / 5) == 0
    )
    assert not get_handler(GROUPS["514520"]["rule"]).diagram_specs(ctx)


@pytest.mark.parametrize("a,c,h", tuple(itertools.product((2, 5), (3, 7), (4, 12))))
def test_box_altitude_independent_of_vertex_orientation(a, c, h):
    for p, q, r in (("A_1", "D_1", "B"), ("D_1", "A_1", "C"), ("B", "A", "C_1")):
        # The third orientation is a reflected edge/face right triangle.
        html = f"<p>Длины ребер AB, AD и AA_1 прямоугольного параллелепипеда ABCDA_1B_1C_1D_1 равны соответственно {a}, {c} и {h}. Докажите, что расстояние от вершины {q} до прямой {p + r} больше, чем расстояние от вершины {p} до прямой {q + r}. Найдите расстояние от вершины {p} до прямой {q + r}.</p>"
        m = read_question(html)
        _, independent = geometry(m)
        assert sp.simplify(independent - m.answer) == 0


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_missing_solution_assets_restore_only_exact_compatible_sources(case):
    ctx = deepcopy(case["context"])
    for sec in ctx["normalized_content"]["sections"]:
        soup = BeautifulSoup(sec["html"], "html.parser")
        for image in soup.find_all("img"):
            image.decompose()
        sec["html"], sec["asset_keys"] = str(soup), []
    ctx["normalized_content"]["assets"] = []
    result = plan(case, ctx)
    replay(ctx, result.transformations)
    assert [
        (a["asset_key"], a["asset_id"]) for a in ctx["normalized_content"]["assets"]
    ] == [
        (a["asset_key"], a["asset_id"])
        for a in case["context"]["normalized_content"]["assets"]
    ]
    assert not plan(case, ctx).transformations


@pytest.mark.parametrize("key", GROUPS)
def test_explicit_profiles_use_same_spatial_distance_runtime(key):
    profile = get_group_profile(key)
    handler = get_handler(profile.content_rule_key)
    assert (
        profile.category_key == "15" and profile.content_rule_key == GROUPS[key]["rule"]
    )
    assert (
        handler.resolve().__module__
        == "solution_runner.pipelines.solids.distance_parent"
    )
