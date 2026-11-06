"""Independent coordinates check the first two new proof families before registration."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import section
from plane_geometry_oracle import foot
from projection_plane_equation_oracle import equal, evaluate, values_for

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.spatial_distance_model import (
    condition_text,
    read_question,
)
from solution_runner.pipelines.solids.spatial_distance_proofs import render

CASES = [
    c
    for c in json.loads(
        (
            Path(__file__).parent / "fixtures/category_15_line_projection_sources.json"
        ).read_text()
    )["cases"]
    if c["group"] in {"500064", "505237"}
]


def plane_normal(p, names):
    a, b, c = (p[n] for n in names)
    return (b - a).cross(c - a)


def geometry(m):
    scale = sp.Rational(7, 3)
    given = dict(m.given)
    if m.mode == "triangle_prism_half_volume_angle":
        a, h = given["a"], given["height"]
        p = {
            "B": sp.zeros(3, 1),
            "C": sp.Matrix([a, 0, 0]),
            "A": sp.Matrix([a / 2, sp.sqrt(3) * a / 2, 0]),
        }
        p.update({n + "_1": v + sp.Matrix([0, 0, h]) for n, v in list(p.items())})
        p.update(D=(p["C"] + p["C_1"]) / 2, K=2 * p["C"] - p["B"])
        p["H"] = foot(p["C"], p["A"], p["K"])
        area = 3 * a * h / 4
        extra = {
            r"S_{AA_1C_1D}": area,
            r"S_{BCDB_1}": area,
            "h_0": sp.sqrt(3) * a / 2,
            r"V_{B_1AA_1C_1D}": a * a * h * sp.sqrt(3) / 8,
            r"V_{ABCDB_1}": a * a * h * sp.sqrt(3) / 8,
            r"\cos60^\circ": sp.Rational(1, 2),
        }
        answer = sp.atan(h / a)
    else:
        rho = given["rho"]
        L = given.get("apothem", sp.denom(rho) * scale)
        R = 2 * L * rho
        h = L * sp.sqrt(1 - rho * rho)
        p = {
            "A": sp.Matrix([R, 0, 0]),
            "B": sp.Matrix([-R / 2, sp.sqrt(3) * R / 2, 0]),
            "C": sp.Matrix([-R / 2, -sp.sqrt(3) * R / 2, 0]),
            "S": sp.Matrix([0, 0, h]),
            "H": sp.zeros(3, 1),
        }
        p["M"] = (p["B"] + p["C"]) / 2
        p["K"] = foot(p["C"], p["S"], p["B"])
        extra = {
            "a": scale,
            r"S_{BSC}": (p["B"] - p["S"]).cross(p["C"] - p["S"]).norm() / 2,
        }
        u, v = plane_normal(p, ("S", "A", "B")), plane_normal(p, ("S", "C", "B"))
        answer = sp.acos(sp.simplify(abs(u.dot(v)) / (u.norm() * v.norm())))
        for name, first, second in [("A", "B", "C"), ("B", "A", "C"), ("C", "A", "B")]:
            assert sp.simplify((p["S"] - p[name]).dot(p[first] - p[second])) == 0
    values = values_for(p, extra)
    for label in ("CHD", "SMH", "AKC"):
        if not all(n in p for n in label):
            continue
        A, B, C = (p[n] for n in label)
        u, v = A - B, C - B
        values[r"\cos\angle " + label] = sp.simplify(u.dot(v) / (u.norm() * v.norm()))
        values[r"\tan\angle " + label] = sp.simplify(u.cross(v).norm() / u.dot(v))
    return p, values, answer


def verify(m, html=None):
    _, values, answer = geometry(m)
    html = render(m, {}) if html is None else html
    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        sides = [evaluate(side, values) for side in formula.split("=")]
        assert len(sides) > 1 and all(equal(sides[0], side) for side in sides), (
            formula,
            sides,
        )
    assert equal(answer, m.answer)
    assert "\\" not in soup.get_text()


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_displayed_equation_uses_independent_geometry(case):
    m = read_question(section(case["context"], "condition")["html"])
    verify(m)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_extra_question_refuses(case):
    with pytest.raises(ContentPlanError):
        read_question(
            section(case["context"], "condition")["html"] + "<p>Найдите ещё объём.</p>"
        )


@pytest.mark.parametrize(
    "raw",
    [
        "Дана правильная треугольная пирамида. Докажите, что ее противоположные ребра перпендикулярны. Пусть косинус угла между боковой гранью и основанием равен 1. Найдите угол между боковыми гранями этой пирамиды.",
        "Дана правильная треугольная пирамида. Докажите, что ее противоположные ребра перпендикулярны. Пусть косинус угла между боковой гранью и основанием равен 0. Найдите угол между боковыми гранями этой пирамиды.",
    ],
)
def test_degenerate_face_cosine_refuses(raw):
    with pytest.raises(ContentPlanError):
        read_question("<p>" + raw + "</p>")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_changed_measurements_recalculate_with_the_same_geometric_method(case):
    import re

    ctx = deepcopy(case["context"])
    html = section(ctx, "condition")["html"]
    m = read_question(html)
    raw = condition_text(html, None)
    if case["group"] == "500064":
        raw = re.sub(r"(стороны основания равны ).+?,", lambda x: x[1] + "5,", raw)
        raw = re.sub(r"(боковые ребра равны ).+?,", lambda x: x[1] + "7,", raw)
    else:
        raw = raw.replace(sp.latex(dict(m.given)["rho"]), r"\frac{1}{3}")
        assert raw != condition_text(html, None)
    changed = read_question("<p>" + raw + "</p>")
    assert changed.given != m.given
    verify(changed)
