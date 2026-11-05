"""Evaluate published formula equalities with exact pi and independent sphere measures."""

import re

import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import solution_html

from solution_runner.pipelines.equations.logarithm_parser import LogarithmParser, Node


class PiParser(LogarithmParser):
    def _nested(self, text):
        return PiParser(text, self.depth + 1).parse()

    def _primary(self):
        if self.text.startswith(r"\pi", self.index):
            self.index += 3
            return Node(sp.pi, r"\pi")
        return super()._primary()


def quantities(m):
    radii = {1: sp.Integer(3), 2: sp.Integer(5)}
    if m.mode in {"surface_factor", "volume_factor"}:
        factor = m.given[0]
        power = 3 if m.input_kind == "volume" else 1
        radii[m.small] = sp.Integer(3)
        radii[m.large] = sp.root(sp.simplify(3**power * factor), power)
        radius = radii[m.large]
    elif m.mode == "combined_radius":
        radii = {i + 1: r for i, r in enumerate(m.given)}
        total = sum(r * r if m.degree == 2 else r * r * r for r in m.given)
        radius = sp.root(total, m.degree)
        radii[len(m.given) + 1] = radius
    elif m.mode == "surface_over_pi":
        radius = sp.root(sp.Rational(3, 4) * m.given[0], 3)
    else:
        radius = sp.sqrt(m.given[0] / sp.pi)
    variables = {
        "R": radius,
        "V": 4 * sp.pi * radius**3 / 3,
        "S": 4 * sp.pi * radius**2,
        "S_0": sp.pi * radius**2,
    }
    for i, r in radii.items():
        variables.update(
            {
                f"R_{i}": r,
                f"V_{i}": 4 * sp.pi * r**3 / 3,
                f"S_{i}": 4 * sp.pi * r**2,
                f"d_{i}": 2 * r,
            }
        )
    return variables


def verify(result, m):
    nodes = BeautifulSoup(solution_html(result), "html.parser").select(
        "[data-inline-latex]"
    )
    assert 5 <= len(nodes) <= 9
    for node in nodes:
        formula = node["data-inline-latex"]
        for name, amount in sorted(quantities(m).items(), key=lambda p: -len(p[0])):
            formula = re.sub(
                r"(?<![A-Za-z_])" + re.escape(name) + r"(?![A-Za-z_0-9])",
                lambda _, v=amount: "(" + sp.latex(v) + ")",
                formula,
            )
        formula = formula.replace(r"\pi", r"(\pi)")
        values = [PiParser(part).parse().value for part in formula.split("=")]
        assert len(values) > 1 and all(
            sp.simplify(v - values[0]) == 0 for v in values
        ), formula
    assert sp.simplify(PiParser(result.answer).parse().value - m.answer) == 0
