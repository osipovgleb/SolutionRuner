"""Evaluate each proof equation, including all three parent sine methods."""

import math
import re

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from test_isosceles_obtuse_model import CASES, GROUPS, condition
from test_isosceles_side_altitude_proofs import angular_values

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.triangles.isosceles.obtuse_model import read_question
from solution_runner.pipelines.triangles.isosceles.obtuse_proofs import (
    render,
    review_parent,
)


def check_rows(html, m):
    points = {
        m.apex: sp.Matrix([0, 0]),
        m.vertex: sp.Matrix([-m.projection, m.height]),
        m.other_base_vertex: sp.Matrix([m.side, 0]),
        "H": sp.Matrix([-m.projection, 0]),
    }
    for row in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        raw = row["data-inline-latex"]

        def function(match):
            sine, cosine = angular_values(points, match[2])
            return (
                "("
                + sp.latex({"sin": sine, "cos": cosine, "tg": sine / cosine}[match[1]])
                + ")"
            )

        text = re.sub(r"\\(sin|cos|tg)\s*\\angle\s*([ABCH]{3})", function, raw)
        text = re.sub(r"\\sin\s+(30|150)\^\{\\circ\}", lambda _: r"(\frac{1}{2})", text)
        approximate = r"\angle" in text

        def angle(match):
            _, cosine = angular_values(points, match[1])
            return "(" + f"{math.degrees(math.acos(float(cosine))):.6f}" + ")"

        text = re.sub(r"\\angle\s*([ABCH]{3})", angle, text).replace(r"^{\circ}", "")

        def length(match):
            value = (points[match[0][0]] - points[match[0][1]]).norm()
            return "(" + sp.latex(sp.simplify(value)) + ")"

        text = re.sub(r"[ABCH]{2}", length, text)
        text = text.replace("S", "(" + sp.latex(m.side * m.height / 2) + ")")
        values = [TrigonometricParser(part).parse().value for part in text.split("=")]
        assert len(values) > 1, raw
        if approximate:
            assert all(abs(float(v - values[0])) < 2e-6 for v in values), raw
        else:
            assert all(sp.simplify(v - values[0]) == 0 for v in values), raw


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_all_native_proof_equations_and_method_order(case):
    m = read_question(*condition(case))
    rule = GROUPS[case["group"]]["rule"]
    parent = next(c for c in CASES if c["task"] == case["group"])
    original = next(
        s["html"]
        for s in parent["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    review_parent(original, rule)
    html = render(m, rule)
    check_rows(html, m)
    titles = [
        s["data-solution-title"]
        for s in BeautifulSoup(html, "html.parser").select("section")
    ]
    assert titles == (
        ["Решение", "Приведём другое решение", "Приведём ещё одно решение"]
        if case["group"] == "27345"
        else ["Решение"]
    )
    if case["group"] == "27345":
        assert (r"150^{\circ}" in html) == (m.answer == sp.Rational(1, 2))
        assert "площадь" in html


@pytest.mark.parametrize("group", list(GROUPS))
def test_changed_parent_methods_fail_closed(group):
    parent = next(c for c in CASES if c["task"] == group)
    original = next(
        s["html"]
        for s in parent["context"]["normalized_content"]["sections"]
        if s["key"] == "solution"
    )
    for changed in [None, "", original + "<p>Другой метод.</p>"]:
        with pytest.raises(ContentPlanError):
            review_parent(changed, GROUPS[group]["rule"])
