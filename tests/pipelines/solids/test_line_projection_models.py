"""Independent vector geometry for the remaining draft projection readers."""

import json
from pathlib import Path

import pytest
import sympy as sp
from midpoint_source_cases import section
from plane_geometry_oracle import foot

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids import box_line_projection_model
from solution_runner.pipelines.solids.spatial_distance_model import (
    condition_text,
    read_question,
)

CASES = [
    c
    for c in json.loads(
        (
            Path(__file__).parent / "fixtures/category_15_line_projection_sources.json"
        ).read_text()
    )["cases"]
    if c["group"] in {"507576", "513098"}
]


def raw_condition(case):
    return condition_text(section(case["context"], "condition")["html"], None)


def read(case, raw=None):
    text = raw_condition(case) if raw is None else raw
    result = (
        box_line_projection_model.read(text)
        if case["group"] == "507576"
        else read_question("<p>" + text + "</p>")
    )
    if result is None:
        raise ContentPlanError("unsupported complete draft condition")
    return result


def coordinates(a, b, h):
    p = {
        "A": sp.zeros(3, 1),
        "B": sp.Matrix([a, 0, 0]),
        "C": sp.Matrix([a, b, 0]),
        "D": sp.Matrix([0, b, 0]),
    }
    return p | {n + "_1": v + sp.Matrix([0, 0, h]) for n, v in p.items()}


def normal(p, names):
    a, b, c = (p[n] for n in names)
    return (b - a).cross(c - a)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_native_projection_answers_and_feet_follow_independent_vectors(case):
    m = read(case)
    assert m is not None
    g = dict(m.given)
    p = coordinates(g["a"], g["b"], g.get("height", g.get("H")))
    if case["group"] == "507576":
        if m.names[0] == "face":
            n = normal(p, ("A_1", "B", "C"))
            line = p["C_1"] - p["B"]
            E = foot(p["C_1"], p["C"], p["D_1"])
            distance = (p["C_1"] - E).norm()
        else:
            n = normal(p, ("A", "A_1", "C"))
            line = p["B"] - p["A_1"]
            E = foot(p["B"], p["A"], p["C"])
            distance = (p["B"] - E).norm()
        sine = sp.simplify(abs(line.dot(n)) / (line.norm() * n.norm()))
        assert sp.simplify(distance / line.norm() - sine) == 0
        assert sp.simplify(sp.sin(m.answer) - sine) == 0
        assert sp.simplify(m.q["helper"] - distance) == 0
        for i, axis in enumerate("xyz"):
            assert sp.simplify(m.q["E_" + axis] - E[i]) == 0
    else:
        S = p["A_1"]
        assert sp.simplify((S - p["B"]).norm() - g["SB"]) == 0
        assert sp.simplify((S - p["D"]).norm() - g["SD"]) == 0
        if m.mode == "rectangular_pyramid_angle":
            assert sp.simplify(sp.tan(m.answer * sp.pi / 180) - g["b"] / g["SB"]) == 0
        else:
            u, v = p["C"] - S, p["D"] - p["B"]
            cosine = sp.simplify(abs(u.dot(v)) / (u.norm() * v.norm()))
            assert sp.simplify(sp.cos(m.answer) - cosine) == 0


@pytest.mark.parametrize(
    "task,old,new",
    [
        ("511478", "AB = 12", "AB = 11"),
        ("507576", "AA_1 = 8", "AA_1 = 0"),
        ("513098", r"SB=3\sqrt{3}", "SB=6"),
        ("515920", r"SD=\sqrt{57}", "SD=7"),
        ("661318", "SB = 9", "SB = 8"),
    ],
)
def test_false_perpendicularity_zero_dimensions_and_unproved_altitude_refuse(
    task, old, new
):
    case = next(c for c in CASES if c["task"] == task)
    raw = raw_condition(case)
    assert old in raw
    with pytest.raises(ContentPlanError):
        read(case, raw.replace(old, new))


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_draft_readers_refuse_extra_requirements(case):
    with pytest.raises(ContentPlanError):
        read(case, raw_condition(case) + " Найдите также объём.")
