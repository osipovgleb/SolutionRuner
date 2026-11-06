"""Exact prism halves and common perpendiculars are checked in actual 3-D coordinates."""

import json
from pathlib import Path

import pytest
import sympy as sp

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.prism_midpoint_volume_model import read
from solution_runner.pipelines.solids.spatial_distance_model import condition_text

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_15_volume_sections_sources.json"
    ).read_text()
)
CASES = [c for c in DATA["cases"] if c["group"] == "501436"]


def raw(case):
    sections = case["context"]["normalized_content"]["sections"]
    return condition_text(
        next(s["html"] for s in sections if s["key"] == "condition"), None
    )


def volume(a, b, c, d):
    return abs(sp.det(sp.Matrix.hstack(b - a, c - a, d - a))) / 6


def verify(result):
    a, h = result.q["a"], result.q["H"]
    A, B, C = (
        sp.zeros(3, 1),
        sp.Matrix([a, 0, 0]),
        sp.Matrix([a / 2, sp.sqrt(3) * a / 2, 0]),
    )
    z = sp.Matrix([0, 0, h])
    A1, B1, C1 = A + z, B + z, C + z
    D = (B + B1) / 2
    lower = volume(C, A, B, D) + volume(C, A, D, A1)
    upper = volume(A1, D, B1, C1) + volume(A1, D, C1, C)
    assert sp.simplify(lower - result.answer) == sp.simplify(upper - result.answer) == 0
    assert sp.simplify(lower + upper - result.q["prism_volume"]) == 0
    normal = (D - A1).cross(C1 - C)
    distance = abs((C - A1).dot(normal)) / normal.norm()
    plane_normal = (C - B).cross(C1 - B)
    point_distance = abs((A - B).dot(plane_normal)) / plane_normal.norm()
    assert sp.simplify(distance - point_distance) == 0
    assert sp.simplify(distance - result.q["base_altitude"]) == 0


@pytest.mark.parametrize("case,expected", list(zip(CASES, (3, 6, 24))))
def test_all_native_pentahedra_and_their_distance_claims(case, expected):
    result = read(raw(case))
    assert result.answer == expected
    assert result.names[0] == ("upper" if case["task"] == "501456" else "lower")
    verify(result)


@pytest.mark.parametrize(
    "a,h", [(2, 3), (5, 1), (7, sp.sqrt(2)), (sp.Rational(3, 2), 8)]
)
def test_changed_dimensions_keep_both_exact_volume_halves(a, h):
    text = (
        raw(CASES[0])
        .replace(r"8\sqrt{3}", sp.latex(h))
        .replace("основания равно 1.", "основания равно " + sp.latex(a) + ".")
    )
    verify(read(text))


@pytest.mark.parametrize(
    "old,new", [("8\\sqrt{3}", "0"), ("основания равно 1.", "основания равно -1.")]
)
def test_nonpositive_prism_dimensions_are_rejected(old, new):
    with pytest.raises(ContentPlanError):
        read(raw(CASES[0]).replace(old, new))


@pytest.mark.parametrize(
    "old,new",
    [
        ("середина ребра BB_1", "середина ребра AA_1"),
        ("плоскостью BCC_1", "плоскостью ABC"),
        ("пятигранника ABCA_1D", "пятигранника ABCA_1B_1"),
        ("Найдите объем", "Найдите площадь"),
    ],
)
def test_different_midpoints_claims_or_requested_objects_do_not_match(old, new):
    assert read(raw(CASES[0]).replace(old, new)) is None
