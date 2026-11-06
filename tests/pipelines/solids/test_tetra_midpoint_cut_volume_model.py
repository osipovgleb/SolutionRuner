"""Tetrahedral determinants independently verify both pieces of each section."""

import json
import re
from pathlib import Path

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from projection_plane_equation_oracle import ScalarParser

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.spatial_distance_model import condition_text
from solution_runner.pipelines.solids.tetra_midpoint_cut_volume_model import read
from solution_runner.pipelines.solids.tetra_midpoint_cut_volume_proof import render

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_15_volume_sections_sources.json"
    ).read_text()
)
CASES = [c for c in DATA["cases"] if c["group"] == "517446"]


def raw(case):
    sections = case["context"]["normalized_content"]["sections"]
    return condition_text(
        next(s["html"] for s in sections if s["key"] == "condition"), None
    )


def volume(a, b, c, d):
    return abs(sp.det(sp.Matrix.hstack(b - a, c - a, d - a))) / 6


@pytest.mark.parametrize(
    "case,expected",
    list(zip(CASES, (sp.Rational(13, 23), sp.Rational(21, 11), sp.Rational(9, 23)))),
)
def test_actual_sources_keep_the_order_of_the_two_volumes(case, expected):
    result = read(raw(case))
    assert result.answer == expected


@pytest.mark.parametrize("u,v", [(1, 2), (3, 1), (1, 3), (2, 2), (5, 7), (9, 1)])
def test_affine_tetrahedra_have_the_computed_volume_ratio(u, v):
    text = raw(CASES[0]).replace("1: 2.", f"{u}: {v}.")
    result = read(text)
    A, B, C, D = map(sp.Matrix, [(1, 2, 3), (4, -1, 2), (-2, 3, 5), (2, 1, 9)])
    t = sp.Rational(u, u + v)
    M, N, P, Q = A + t * (B - A), C + t * (B - C), (D + A) / 2, (D + C) / 2
    assert (M - P).dot((Q - P).cross(N - P)) == 0
    left = volume(P, A, C, N) + volume(P, A, N, M) + volume(P, Q, C, N)
    total = volume(A, B, C, D)
    assert sp.simplify(left / total - result.q["left_volume"]) == 0
    assert sp.simplify(left / (total - left) - result.answer) == 0


@pytest.mark.parametrize("ratio", ["0: 2", "-1: 2", "1: 0", "1: -2"])
def test_nonpositive_edge_ratios_are_rejected(ratio):
    with pytest.raises(ContentPlanError):
        read(raw(CASES[0]).replace("1: 2.", ratio + "."))


@pytest.mark.parametrize(
    "old,new",
    [
        ("DA и DC", "DB и DC"),
        ("CN: NB", "CN: NC"),
        ("плоскость PQM", "плоскость PQB"),
        ("одной плоскости.", "одной плоскости. Еще одно требование."),
    ],
)
def test_different_edges_claims_and_trailing_instructions_do_not_match(old, new):
    assert read(raw(CASES[0]).replace(old, new)) is None


def triangle_area(a, b, c):
    return (b - a).cross(c - a).norm() / 2


def geometric_values(result):
    A, B, C, D = map(sp.Matrix, [(1, 2, 3), (4, -1, 2), (-2, 3, 5), (2, 1, 9)])
    u, v = dict(result.given).values()
    t = u / (u + v)
    p = {"A": A, "B": B, "C": C, "D": D}
    p.update(M=A + t * (B - A), N=C + t * (B - C), P=(D + A) / 2, Q=(D + C) / 2)
    areas = {
        name: triangle_area(*(p[n] for n in name))
        for name in ("QCN", "BCD", "MBN", "ABC")
    }
    areas["ACNM"] = areas["ABC"] - areas["MBN"]
    volumes = {"PQCN": volume(p["P"], p["Q"], C, p["N"])}
    volumes["PACNM"] = volume(p["P"], A, C, p["N"]) + volume(p["P"], A, p["N"], p["M"])
    volumes["APMNCQ"] = volumes["PQCN"] + volumes["PACNM"]
    volumes["BMNDPQ"] = volume(A, B, C, D) - volumes["APMNCQ"]
    return {
        **{"S_{" + name + "}": area for name, area in areas.items()},
        **{"V_{" + name + "}": amount for name, amount in volumes.items()},
        **{
            name: (p[name[0]] - p[name[1]]).norm()
            for name in ("BM", "BA", "BN", "BC", "CN", "CB", "CQ", "CD")
        },
        "V": volume(A, B, C, D),
    }


@pytest.mark.parametrize("case", CASES)
def test_every_printed_equation_matches_independent_lengths_areas_and_volumes(case):
    result = read(raw(case))
    values = geometric_values(result)
    html = render(result, {})
    equations = BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    assert len(equations) == 9
    for node in equations:
        raw_equation = node["data-inline-latex"]
        for name, number in sorted(values.items(), key=lambda item: -len(item[0])):
            raw_equation = raw_equation.replace(name, "(" + sp.latex(number) + ")")
        raw_equation = re.sub(r"\\frac([12])([12])", r"\\frac{\1}{\2}", raw_equation)
        terms = [ScalarParser(term).parse().value for term in raw_equation.split("=")]
        assert all(sp.simplify(term - terms[0]) == 0 for term in terms), node
