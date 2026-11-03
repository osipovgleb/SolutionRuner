"""Independent positive coordinate model for both right-triangle source families."""

import re

import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.triangles.right.altitude_input import canonical_condition
from solution_runner.pipelines.triangles.right.altitude_solver import (
    _parse_positive_value,
)

U, V = sp.symbols("u v", positive=True)


def coordinate_values(html, *, source):
    html = canonical_condition(html, source=source)
    known = {}
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        if "=" in formula:
            key, value = formula.split("=", 1)
            known[key.replace("\\", "").replace(" ", "")] = _parse_positive_value(value)
    squares = {
        "AB": (U + V) ** 2,
        "AH": U**2,
        "BH": V**2,
        "CH": U * V,
        "AC": U * (U + V),
        "BC": V * (U + V),
        "sinA": V / (U + V),
        "cosA": U / (U + V),
        "tgA": V / U,
        "sinB": U / (U + V),
        "cosB": V / (U + V),
        "tgB": U / V,
    }
    equations = [
        sp.together(squares[key] - number**2).as_numer_denom()[0]
        for key, number in known.items()
    ]
    roots = [
        root
        for root in sp.solve(equations, (U, V), dict=True)
        if root[U].is_positive and root[V].is_positive
    ]
    assert len(roots) == 1
    values = {
        key: sp.simplify(sp.sqrt(value.subs(roots[0])))
        for key, value in squares.items()
    }
    return values


def numeric_formula(text, values):
    if "x" in values:
        text = re.sub(
            r"(?<![A-Za-z])x(?![A-Za-z])",
            lambda _: "(" + sp.latex(values["x"]) + ")",
            text,
        )

    def trig(match):
        angle = match[3] or match[4]
        angle = (
            "A"
            if angle in {"HCB", "BCH"}
            else "B"
            if angle in {"HCA", "ACH"}
            else angle
        )
        value = "(" + sp.latex(values[match[1] + angle]) + ")"
        return value + ("^" + match[2] if match[2] else "")

    text = re.sub(
        r"\\(sin|cos|tg)(?:\^\{?(\d+)\}?)?\s*(?:\\angle\s*(HCB|BCH|HCA|ACH)|([AB]))",
        trig,
        text,
    )
    aliases = {"BA": "AB", "CA": "AC", "CB": "BC", "HA": "AH", "HB": "BH", "HC": "CH"}
    return re.sub(
        r"AB|BA|AC|CA|BC|CB|AH|HA|BH|HB|CH|HC",
        lambda m: "(" + sp.latex(values[aliases.get(m[0], m[0])]) + ")",
        text,
    )
