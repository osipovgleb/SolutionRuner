"""Check all scalar, coordinate and vector formulas against independent geometry."""

import re

import pytest
import sympy as sp
from bs4 import BeautifulSoup
from projection_plane_equation_oracle import equal
from round_solid_geometry import axis_chord, concentric, insphere, rectangle
from round_solid_source_cases import CASES, changed, raw
from skew_line_equation_oracle import evaluate as scalar_or_vector
from skew_line_equation_oracle import vector_values
from test_round_solid_models import READERS

from solution_runner.pipelines.solids import (
    concentric_sphere_section_proof,
    cylinder_axis_chord_proof,
    cylinder_rectangle_volume_proof,
    hex_pyramid_insphere_proof,
)
from solution_runner.pipelines.word_problems.common import UnsupportedCondition

FAMILIES = {
    "502115": (concentric_sphere_section_proof, concentric),
    "520803": (cylinder_axis_chord_proof, axis_chord),
    "520938": (cylinder_axis_chord_proof, axis_chord),
    "502023": (hex_pyramid_insphere_proof, insphere),
    "514026": (cylinder_rectangle_volume_proof, rectangle),
}


def evaluate(term, values, vectors):
    try:
        return scalar_or_vector(term, values, vectors)
    except UnsupportedCondition as exc:
        raise AssertionError(term) from exc


def verify(group, text):
    m = READERS[group](text)
    proof, geometry = FAMILIES[group]
    points, values, answer = geometry(m)
    html = proof.render(m, {})
    vectors = {
        r"\overrightarrow{" + a + b + "}": B - A
        for a, A in points.items()
        for b, B in points.items()
        if a != b
    }
    values.update(vector_values(vectors, html))
    equations = BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    assert len(equations) >= 4
    for node in equations:
        formula = re.sub(
            r"([0-9]+)\^\{\\circ\}", r"(\1\\pi/180)", node["data-inline-latex"]
        )
        formula = re.sub(r"\\le(?![A-Za-z])", "<=", formula)
        if re.match(r"[A-Z](?:_1)?\(", formula):
            for component in formula.split(r",\quad "):
                name, coordinates = component.split("(", 1)
                actual = sp.Matrix(
                    [evaluate(c, values, {}) for c in coordinates[:-1].split(";")]
                )
                assert sp.simplify(actual - points[name]).is_zero_matrix, component
            continue
        for equation in formula.split(r",\quad "):
            terms = re.split(r"(<=|>=|=|<|>)", equation)
            results = []
            for term in terms[::2]:
                if ";" in term:
                    results.append(
                        sp.Matrix(
                            [
                                evaluate(c, values, {})
                                for c in term.strip()[1:-1].split(";")
                            ]
                        )
                    )
                else:
                    results.append(evaluate(term, values, vectors))
            for operator, first, second in zip(terms[1::2], results, results[1:]):
                if isinstance(first, sp.MatrixBase):
                    assert (
                        operator == "=" and sp.simplify(first - second).is_zero_matrix
                    ), node
                elif operator == "=":
                    assert equal(first, second), (node, first, second)
                else:
                    relation = {"<=": sp.Le, ">=": sp.Ge, "<": sp.Lt, ">": sp.Gt}[
                        operator
                    ]
                    assert relation(first, second) == sp.S.true, (node, first, second)
    assert equal(m.answer, answer)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["task"])
def test_every_native_formula_coordinate_and_vector(case):
    verify(case["group"], raw(case["task"]))


@pytest.mark.parametrize(
    "group,task,changes",
    [
        (
            "502115",
            "502115",
            [("равна 8.", r"равна 3\pi."), ("равна 5.", r"равна 2\pi.")],
        ),
        (
            "520803",
            "520803",
            [
                ("AB = 6", "AB = 5"),
                ("BB_1 = 15", "BB_1 = 7"),
                ("B_1C_1 = 8", "B_1C_1 = 12"),
            ],
        ),
        (
            "520803",
            "520879",
            [
                ("AB = 21", "AB = 3"),
                ("BB_1 = 12", "BB_1 = 4"),
                ("B_1C_1 = 16", "B_1C_1 = 5"),
            ],
        ),
        (
            "520803",
            "520803",
            [
                ("AB = 6", "AB = 3"),
                ("BB_1 = 15", "BB_1 = 5"),
                ("B_1C_1 = 8", "B_1C_1 = 4"),
            ],
        ),
        ("502023", "502023", [("равно 10,", "равно 15,"), ("равна 6,", "равна 9,")]),
        (
            "514026",
            "514026",
            [("высотой 12", "высотой 5"), ("основания 6", "основания 3")],
        ),
    ],
)
def test_changed_dimensions_recompute_every_printed_formula(group, task, changes):
    verify(group, changed(task, *changes))
