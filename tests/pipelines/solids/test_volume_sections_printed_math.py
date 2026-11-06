"""Every displayed equality and strict inequality is checked, including changed ratios."""

import re

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from projection_plane_equation_oracle import ScalarParser, equal
from volume_sections_geometry import hexagon, perpendicular, prism
from volume_sections_source_cases import raw, replace

from solution_runner.pipelines.solids import (
    hexagonal_pyramid_skew_model,
    hexagonal_pyramid_skew_proof,
    perpendicular_triangle_volume_model,
    perpendicular_triangle_volume_proof,
    prism_midpoint_volume_model,
    prism_midpoint_volume_proof,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

FAMILIES = {
    "hexagon": (hexagonal_pyramid_skew_model, hexagonal_pyramid_skew_proof, hexagon),
    "prism": (prism_midpoint_volume_model, prism_midpoint_volume_proof, prism),
    "perpendicular": (
        perpendicular_triangle_volume_model,
        perpendicular_triangle_volume_proof,
        perpendicular,
    ),
}
NATIVE = [("hexagon", task) for task in ("484567", "511467", "507675")]
NATIVE += [("prism", task) for task in ("501436", "501456", "511360")]
NATIVE += [("perpendicular", task) for task in ("501549", "501555", "505241", "511363")]


def evaluate(text, values):
    text = text.replace(r"\cos60^{\circ}", r"\frac{1}{2}").replace(
        r"60^{\circ}", r"\frac{\pi}{3}"
    )
    text = re.sub(r"\\frac([123])([123])", r"\\frac{\1}{\2}", text)
    text = re.sub(r"\\sqrt([23])", r"\\sqrt{\1}", text)
    for name, number in sorted(values.items(), key=lambda item: -len(item[0])):
        text = text.replace(name, "(" + sp.latex(number) + ")")
    text = text.replace(r"\operatorname{acos}", r"\arccos")
    try:
        return sp.simplify(ScalarParser(text).parse().value)
    except UnsupportedCondition as exc:
        raise AssertionError(text) from exc


def verify(family, text):
    model, proof, geometry = FAMILIES[family]
    m = model.read(text)
    values = geometry(m)
    equations = BeautifulSoup(proof.render(m, {}), "html.parser").select(
        "[data-inline-latex]"
    )
    assert len(equations) >= 3
    for node in equations:
        terms = re.split(r"([=<>])", node["data-inline-latex"])
        left = evaluate(terms[0], values)
        for operator, right in zip(terms[1::2], terms[2::2]):
            right = evaluate(right, values)
            assert (
                equal(left, right)
                if operator == "="
                else left > right
                if operator == ">"
                else left < right
            ), node
            left = right


@pytest.mark.parametrize("family,task", NATIVE)
def test_every_native_printed_equation_matches_actual_geometry(family, task):
    verify(family, raw(task))


@pytest.mark.parametrize(
    "division,claim", [("1: 1", "1: 1"), ("5: 2", "4: 7"), ("1: 2", "4: 3")]
)
def test_other_median_divisions_use_valid_geometric_proofs(division, claim):
    verify(
        "perpendicular",
        replace(
            "501549",
            ("BT: TM = 3: 1", "BT: TM = " + division),
            ("отношении 1: 2", "отношении " + claim),
        ),
    )


def test_non_equilateral_lateral_triangle_uses_the_actual_angle():
    verify(
        "hexagon",
        replace("484567", ("равны 1,", "равны 3,"), ("равны 2,", "равны 10,")),
    )
