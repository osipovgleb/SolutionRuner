"""Independent point geometry checks every preserved side-altitude proof row."""

import math
import re

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from isosceles_altitude_cases import CASES, GROUPS, PARENTS, model, section
from test_isosceles_side_altitude_model import PARAMETERS, projection_geometry

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.isosceles.side_altitude_model import (
    RULES,
    read_question,
)
from solution_runner.pipelines.triangles.isosceles.side_altitude_proofs import (
    render,
    review_parent,
)


def points(m, oracle):
    x, y = (
        sp.simplify(oracle["side"] * oracle["cos"]),
        sp.simplify(oracle["side"] * oracle["sin"]),
    )
    p, q, r = sp.Matrix([-x, 0]), sp.Matrix([x, 0]), sp.Matrix([0, y])
    h = sp.simplify(q + oracle["foot_parameter"] * (r - q))
    return {
        m.vertex: p,
        m.other_base_vertex: q,
        m.apex: r,
        "H": h,
        "K": sp.Matrix([0, 0]),
    }


def angular_values(p, name):
    if len(name) == 1:
        center = name
        ends = sorted(set("ABC") - {center})
    else:
        ends = [name[0], name[2]]
        center = name[1]
    u, v = p[ends[0]] - p[center], p[ends[1]] - p[center]
    norm = sp.sqrt(u.dot(u) * v.dot(v))
    assert norm.is_positive
    cosine = sp.simplify(u.dot(v) / norm)
    sine = sp.simplify(abs(u[0] * v[1] - u[1] * v[0]) / norm)
    return sine, cosine


def verify_rows(html, m, oracle):
    p = points(m, oracle)
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        raw = node["data-inline-latex"]
        text = raw

        def function(match):
            sine, cosine = angular_values(p, match[2])
            value = {
                "sin": sine,
                "cos": cosine,
                "tg": sine / cosine,
                "ctg": cosine / sine,
            }[match[1]]
            return "(" + sp.latex(sp.simplify(value)) + ")"

        text = re.sub(r"\\(sin|cos|tg|ctg)\s*\\angle\s*([ABCHK]{1,3})", function, text)
        approximate = r"\angle" in text

        def degree(match):
            _, cosine = angular_values(p, match[1])
            value = math.degrees(math.acos(max(-1, min(1, float(cosine)))))
            return "(" + f"{value:.6f}" + ")"

        text = re.sub(r"\\angle\s*([ABCHK]{1,3})", degree, text).replace(
            r"^{\circ}", ""
        )

        def length(match):
            a, b = p[match[0][0]], p[match[0][1]]
            return "(" + sp.latex(sp.simplify(sp.sqrt((a - b).dot(a - b)))) + ")"

        text = re.sub(r"[ABCHK]{2}", length, text)
        values = [TrigonometricParser(part).parse().value for part in text.split("=")]
        assert len(values) >= 2, raw
        if approximate:
            assert all(abs(float(v - values[0])) < 2e-6 for v in values), raw
        else:
            assert all(sp.simplify(v - values[0]) == 0 for v in values), raw


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_each_native_proof_equation_and_method_title_matches_geometry(case):
    m = model(case)
    rule = GROUPS[case["group"]]["rule"]
    parent = section(PARENTS[case["group"]]["context"], "solution")["html"]
    review_parent(parent, rule)
    html = render(m, rule)
    verify_rows(html, m, projection_geometry(*PARAMETERS[case["task"]]))
    titles = [
        s["data-solution-title"]
        for s in BeautifulSoup(html, "html.parser").select("section")
    ]
    expected = ["Решение"]
    if case["group"] == "27323":
        expected += ["Альтернативное решение."]
    if case["group"] == "27326":
        expected += ["Приведем другое решение"]
    assert titles == expected
    if case["group"] == "27324":
        assert r"\ctg" in html
    if case["group"] == "27327":
        assert "Примечание" in html and "тупоугольный" in html


@pytest.mark.parametrize("group", list(GROUPS))
def test_parent_methods_and_notes_cannot_silently_change(group):
    rule = GROUPS[group]["rule"]
    parent = section(PARENTS[group]["context"], "solution")["html"]
    with pytest.raises(ContentPlanError):
        review_parent(parent + "<p>Другой метод.</p>", rule)
    with pytest.raises(ContentPlanError):
        review_parent("", rule)


@pytest.mark.parametrize("rule", list(RULES)[:10])
def test_coincident_foot_proof_contains_no_false_strict_inequalities(rule):
    kind, function, request = RULES[rule]
    raw = r"\frac{\sqrt{2}}{2}" if function in {"sin", "cos"} else "1"
    given = "AC=BC=5" if kind == "side" else r"AC=BC, AB=10\sqrt{2}"
    target = "высоту AH" if request == "height" else "BH"
    m = read_question(
        "<p>В треугольнике ABC "
        + given
        + ", AH — высота, \\"
        + function
        + " BAC="
        + raw
        + ". Найдите "
        + target
        + ".</p>",
        "",
    )
    html = render(m, rule)
    oracle = projection_geometry(
        kind,
        5 if kind == "side" else 10 * sp.sqrt(2),
        function,
        sp.sqrt(2) / 2 if function in {"sin", "cos"} else 1,
    )
    verify_rows(html, m, oracle)
    assert "H совпадает с вершиной C" in html
    if "27327" in rule:
        assert "H совпадает с C" in html and "больше длины" not in html


@pytest.mark.parametrize(
    "raw,expected",
    [
        (r"\frac{1}{2}", "тупоугольный"),
        (r"\frac{\sqrt{3}}{2}", "остроугольный"),
        (r"\frac{\sqrt{2}}{2}", "прямоугольный"),
    ],
)
def test_parent_note_is_adapted_to_internal_external_and_coincident_foot(raw, expected):
    rule = "isosceles-triangle-27327-projection-from-side-sine"
    m = read_question(
        "<p>В треугольнике ABC AC=BC=12, AH — высота, \\sin BAC="
        + raw
        + ". Найдите BH.</p>",
        "",
    )
    html = render(m, rule)
    assert "<b>Примечание</b>" in html and expected in html
    oracle = projection_geometry(
        "side",
        12,
        "sin",
        {
            "тупоугольный": sp.Rational(1, 2),
            "остроугольный": sp.sqrt(3) / 2,
            "прямоугольный": sp.sqrt(2) / 2,
        }[expected],
    )
    verify_rows(html, m, oracle)
