"""Evaluate all published equalities against geometric parts and an independent voxel volume."""

import re

import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import solution_html
from sphere_formula_oracle import PiParser
from test_orthogonal_geometry import voxel_measures


def verify(result, m, orders):
    first = m.parts[0].dimensions
    variables = {
        "a_1": first[orders[0][0]],
        "b_1": first[orders[0][1]],
        "c_1": first[orders[0][2]],
    }
    variables.update({"V_" + str(i): p.volume for i, p in enumerate(m.parts, 1)})
    variables.update(
        {"d_" + str(i): a - b for i, (a, b) in enumerate(m.differences, 1)}
    )
    volume = voxel_measures(m.solid.additions, m.solid.cutouts)[0]
    variables["V"] = volume
    soup = BeautifulSoup(solution_html(result), "html.parser")
    nodes = soup.select("[data-inline-latex]")
    paragraphs = [
        p for p in soup.find_all("p") if not p.select_one("[data-inline-latex]")
    ]
    assert 5 <= len(nodes) <= 9 and 2 <= len(paragraphs) <= 4
    for node in nodes:
        formula = node["data-inline-latex"].replace(
            "a_1b_1c_1", r"a_1\cdot b_1\cdot c_1"
        )
        for name, amount in sorted(variables.items(), key=lambda p: -len(p[0])):
            formula = re.sub(
                r"(?<![A-Za-z_\\])" + re.escape(name) + r"(?![A-Za-z_0-9])",
                lambda _, v=amount: "(" + sp.latex(v) + ")",
                formula,
            )
        terms = [PiParser(v).parse().value for v in formula.split("=")]
        assert len(terms) >= 2 and all(t == terms[0] for t in terms), formula
    assert PiParser(result.answer).parse().value == volume
