"""Independent regular-solid constructions and every displayed proof equality."""

import re
from copy import deepcopy

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from metric_source_cases import CASES, GROUPS, plan, read
from midpoint_source_cases import replay, section, solution_html

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser

EXPECTED = {
    "484573": 3,
    "484574": 2 * sp.sqrt(2),
    "511291": sp.Rational(9, 2),
    "511292": sp.Rational(3, 2),
    "507763": sp.sqrt(39) / 4,
    "511484": sp.sqrt(39) / 2,
    "507766": sp.sqrt(3),
    "507778": sp.sqrt(95) / 10,
    "511491": 4 * sp.sqrt(21) / 5,
    "507785": 4 * sp.sqrt(5) / 5,
    "503000": sp.sqrt(6) / 2,
    "503128": sp.sqrt(42) / 14,
    "511380": sp.sqrt(210) / 14,
}


def altitude(p, q, r):
    return q + (p - q).dot(r - q) / (r - q).dot(r - q) * (r - q)


def geometry(m):
    q = m.q
    a = q["a"]
    h = q["H"]
    if m.mode == "tetra_midpoint_distance":
        points = {
            "A": sp.Matrix([0, sp.sqrt(3) * a / 3, 0]),
            "B": sp.Matrix([-a / 2, -sp.sqrt(3) * a / 6, 0]),
            "C": sp.Matrix([a / 2, -sp.sqrt(3) * a / 6, 0]),
            "D": sp.Matrix([0, 0, h]),
            "O": sp.zeros(3, 1),
        }
        A, B, C, D = (points[n] for n in "ABCD")
        points.update(
            P=(B + D) / 2,
            M=(A + C) / 2,
            T=(A + (D if m.names[0] == "AD" else B)) / 2,
            Q=(B + C) / 2 if m.names[0] == "AD" else (C + D) / 2,
        )
        p, t, v = (points[n] for n in ("P", "M", "T"))
        assert (
            sp.simplify((points["P"] - points["T"]).dot(points["M"] - points["T"])) == 0
        )
        return points, sp.simplify((p - t).cross(v - t).norm() / (v - t).norm())
    if m.mode == "hex_vertex_line_distance":
        points = {
            n: sp.Matrix([a * sp.cos(i * sp.pi / 3), a * sp.sin(i * sp.pi / 3), 0])
            for i, n in enumerate("ABCDEF")
        }
        points.update(S=sp.Matrix([0, 0, h]), O=sp.zeros(3, 1))
        x, u, v, y, z = m.names
        assert sp.simplify((points[x] - points["S"]).dot(points[v] - points[u])) == 0
        points["H"] = (points[y] + points[z]) / 2
        points["M"] = altitude(points[y], points["S"], points[z])
        assert sp.simplify((points[y] - points["M"]).dot(points[z] - points["S"])) == 0
        return points, sp.simplify((points[y] - points["M"]).norm())
    points = {
        "A": sp.Matrix([0, sp.sqrt(3) * a / 2, 0]),
        "B": sp.Matrix([-a / 2, 0, 0]),
        "C": sp.Matrix([a / 2, 0, 0]),
    }
    points.update({n + "_1": p + sp.Matrix([0, 0, h]) for n, p in list(points.items())})
    if m.mode == "prism_plane_altitude":
        center = m.names[0]
        other = "B" if center == "A" else "A"
        p = points[other + "_1"]
        t = points[center]
        v = points["C_1"]
        points["M"] = (p + v) / 2
        points["H"] = altitude(p, t, v)
        normal = (p - t).cross(v - t)
        first, second = (
            (points["A_1"], points["B"])
            if center == "A"
            else (points["A"], points["B_1"])
        )
        assert sp.simplify((first - t).dot(normal) + (second - t).dot(normal)) == 0
        return points, sp.simplify((p - points["H"]).norm())
    points["L"] = (points["B"] + points["C"]) / 2
    points["M"] = (points["B_1"] + points["C_1"]) / 2
    points["O"] = (points["A"] + points["M"]) / 2
    points["P"] = altitude(points["O"], points["A_1"], points["B"])
    u = points["B"] - points["A_1"]
    v = points["M"] - points["A"]
    normal = u.cross(points["C"] - points["A_1"])
    assert sp.simplify(normal.cross(v).norm()) == 0
    independent = sp.simplify(
        abs((points["A"] - points["A_1"]).dot(u.cross(v))) / u.cross(v).norm()
    )
    assert independent == sp.simplify((points["O"] - points["P"]).norm())
    return points, independent


def verify(html, m):
    points, independent = geometry(m)
    values = {
        a + b: sp.simplify((p - q).norm())
        for a, p in points.items()
        for b, q in points.items()
        if a != b
    }
    values.update(a=m.q["a"], h=m.q["H"])
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        for symbol, number in sorted(values.items(), key=lambda x: -len(x[0])):
            formula = re.sub(
                r"(?<![A-Za-z_])" + re.escape(symbol) + r"(?![A-Za-z_])",
                lambda _, v=number: "(" + sp.latex(v) + ")",
                formula,
            )
        parts = [TrigonometricParser(p).parse().value for p in formula.split("=")]
        assert len(parts) > 1, formula
        assert all(sp.simplify(v - parts[0]) == 0 for v in parts), formula
    return independent


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_methods_geometry_equalities_and_repeat_preparation(case):
    ctx = deepcopy(case["context"])
    result = plan(case, ctx)
    m = read(ctx)
    assert sp.simplify(m.answer - EXPECTED[case["task"]]) == 0
    assert verify(solution_html(result), m) == EXPECTED[case["task"]]
    assert ctx == case["context"]
    updated = deepcopy(ctx)
    replay(updated, result.transformations)
    assert not plan(case, updated).transformations
    for key in ("condition", "source", "criteria"):
        assert section(updated, key) == section(ctx, key)
    images = BeautifulSoup(solution_html(result), "html.parser").find_all("img")
    assert len(images) == (2 if case["group"] == "503000" else 1)
    assert (
        len(
            BeautifulSoup(solution_html(result), "html.parser").select(
                'ol[data-layout="source-subparts"] > li'
            )
        )
        == 2
    )
    if case["task"] != "507766":
        assert (
            updated["normalized_content"]["assets"]
            == ctx["normalized_content"]["assets"]
        )
    assert bool(get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx)) == (
        case["task"] == "507766"
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize(
    "suffix", (" Найдите также объём.", " Докажите дополнительное утверждение.")
)
def test_extra_unread_geometry_is_refused(case, suffix):
    ctx = deepcopy(case["context"])
    section(ctx, "condition")["html"] += "<p>" + suffix + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)


@pytest.mark.parametrize(
    "case", [c for c in CASES if c["group"] == "503000"], ids=lambda c: c["task"]
)
def test_missing_native_answer_is_derived_and_prepared(case):
    assert section(case["context"], "answer") is None
    result = plan(case)
    answer = next(
        t
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:answer")
    )
    assert (
        answer["operation"] == "add" and "data-inline-latex" in answer["value"]["html"]
    )
    assert (
        verify(solution_html(result), read(case["context"])) == EXPECTED[case["task"]]
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_parent_method_pin_drift_is_refused(case):
    with pytest.raises(ContentPlanError):
        plan(case, parent_solution_html="changed")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
@pytest.mark.parametrize("factor", (sp.Rational(1, 3), sp.Rational(3, 2)))
def test_scaled_native_questions_keep_the_parent_method(case, factor):
    from solution_runner.pipelines.solids.measurements import positive
    from solution_runner.pipelines.solids.spatial_distance_model import condition_text

    ctx = deepcopy(case["context"])
    m = read(ctx)
    raw = condition_text(section(ctx, "condition")["html"], None)
    matches = list(re.finditer(r"(равн[аоы]\s+)(.+?)(?=[,.](?:\s|$))", raw))[
        : len(m.given)
    ]
    assert len(matches) == len(m.given)
    for match in reversed(matches):
        latex = sp.latex(positive(match[2]) * factor)
        raw = (
            raw[: match.start(2)]
            + '<span data-inline-latex="'
            + latex
            + '"></span>'
            + raw[match.end(2) :]
        )
    section(ctx, "condition")["html"] = "<p>" + raw + "</p>"
    scaled = read(ctx)
    result = plan(case, ctx)
    assert sp.simplify(scaled.answer - factor * m.answer) == 0
    assert sp.simplify(verify(solution_html(result), scaled) - factor * m.answer) == 0


@pytest.mark.parametrize(
    "task,old,new",
    (
        ("507763", "AC", "AB"),
        ("507778", "AB_1C_1", "BA_1C_1"),
        ("503000", "является квадратом", "является прямоугольником"),
    ),
)
def test_changed_proof_claim_is_not_silently_used(task, old, new):
    from solution_runner.pipelines.solids.spatial_distance_model import condition_text

    case = next(c for c in CASES if c["task"] == task)
    ctx = deepcopy(case["context"])
    raw = condition_text(section(ctx, "condition")["html"], None)
    assert old in raw
    section(ctx, "condition")["html"] = "<p>" + raw.replace(old, new) + "</p>"
    with pytest.raises(ContentPlanError):
        plan(case, ctx)
