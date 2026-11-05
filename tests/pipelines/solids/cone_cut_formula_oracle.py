"""Check every cut-cone equality against its independently computed full volume."""

import re

import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import solution_html
from sphere_formula_oracle import PiParser


def verify(result, m):
    radius, height, label = m.given
    kept = label if m.kind == "kept" else 360 - label
    full = sp.pi * radius * radius * height / 3
    variables = {
        r"V_{\mathrm{кон}}": full,
        r"\alpha": kept,
        "k": kept / 360,
        "r": radius,
        "h": height,
        "V": full * kept / 360,
    }
    nodes = BeautifulSoup(solution_html(result), "html.parser").select(
        "[data-inline-latex]"
    )
    assert 5 <= len(nodes) <= 9
    for node in nodes:
        formula = (
            node["data-inline-latex"]
            .replace(r"^\circ", "")
            .replace("r^2h", r"r^2\cdot h")
            .replace("kV_", r"k\cdot V_")
        )
        for name, amount in sorted(variables.items(), key=lambda p: -len(p[0])):
            formula = re.sub(
                r"(?<![A-Za-z_\\])" + re.escape(name) + r"(?![A-Za-z_0-9])",
                lambda _, v=amount: "(" + sp.latex(v) + ")",
                formula,
            )
        formula = formula.replace(r"\pi", r"(\pi)")
        values = [PiParser(part).parse().value for part in formula.split("=")]
        assert len(values) > 1 and all(
            sp.simplify(v - values[0]) == 0 for v in values
        ), formula
    assert (
        sp.simplify(PiParser(result.answer).parse().value - variables["V"] / sp.pi) == 0
    )
