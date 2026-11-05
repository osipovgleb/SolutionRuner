"""Evaluate every published equality using actual endpoint distances and requested angles."""

import itertools
import re

import sympy as sp
from bs4 import BeautifulSoup
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.solids.orthogonal_element_geometry import squared


def verify(m, html):
    soup = BeautifulSoup(html, "html.parser")
    formulas = soup.select("[data-inline-latex]")
    paragraphs = [
        p for p in soup.find_all("p") if not p.select_one("[data-inline-latex]")
    ]
    assert 5 <= len(formulas) <= 9
    assert 2 <= len(paragraphs) <= 4
    names = sorted(
        (a + b for a, b in itertools.permutations(m.points, 2)), key=lambda s: -len(s)
    )
    pattern = re.compile(
        r"(?<![A-Za-z_\\])(?:" + "|".join(map(re.escape, names)) + r")(?![A-Za-z_0-9])"
    )
    for node in formulas:
        formula = node["data-inline-latex"]
        angle = r"\angle " + m.requested
        formula = (
            formula.replace(r"\tg" + angle, sp.latex(m.value))
            .replace(angle, sp.latex(m.value))
            .replace(r"^\circ", "")
        )
        formula = pattern.sub(
            lambda match: (
                r"\left(" + sp.latex(sp.sqrt(squared(m.points, match[0]))) + r"\right)"
            ),
            formula,
        )
        terms = [PiParser(part).parse().value for part in formula.split("=")]
        assert len(terms) >= 2 and all(sp.simplify(t - terms[0]) == 0 for t in terms), (
            m.requested,
            formula,
        )
