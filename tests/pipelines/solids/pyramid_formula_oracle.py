"""Evaluate every published equality after independently checking the geometric dimensions."""

import re

import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import solution_html
from pyramid_ratio_oracle import quantities as ratio_quantities
from pyramid_regular_oracle import basic, other, regular
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.solids.pyramid_proofs import BASE, RATIOS
from solution_runner.pipelines.word_problems.common import UnsupportedCondition


def verify(result, m):
    variables, expected = (
        basic(m)
        if m.kind in BASE
        else ratio_quantities(m)
        if m.kind in RATIOS
        else other(m)
        if m.kind in {"perpendicular", "perpendicular_face", "floor"}
        else regular(m)
    )
    nodes = BeautifulSoup(solution_html(result), "html.parser").select(
        "[data-inline-latex]"
    )
    assert 5 <= len(nodes) <= 9, (m.kind, len(nodes))
    for node in nodes:
        formula = node["data-inline-latex"]
        angle = m.q.get("alpha", sp.Integer(45))
        formula = (
            formula.replace(
                r"\tan\alpha", "(" + sp.latex(sp.tan(angle * sp.pi / 180)) + ")"
            )
            .replace(r"\cot60^{\circ}", "(" + sp.latex(sp.sqrt(3) / 3) + ")")
            .replace(r"^{\circ}", "")
        )
        formula = formula.replace(r"\alpha", "(" + sp.latex(angle) + ")")
        for old, new in (
            ("B_1H_1", r"B_1\cdot H_1"),
            ("B_0H_0", r"B_0\cdot H_0"),
            ("B_pH_p", r"B_p\cdot H_p"),
            ("a_1h_1", r"a_1\cdot h_1"),
            ("BH", r"B\cdot H"),
            ("ab", r"a\cdot b"),
            ("xy", r"x\cdot y"),
            ("uv", r"u\cdot v"),
            ("Pl", r"P\cdot l"),
            ("Ph", r"P\cdot h"),
            ("pl", r"p\cdot l"),
            ("ph", r"p\cdot h"),
            ("al", r"a\cdot l"),
            ("ah", r"a\cdot h"),
            ("ka_0", r"k\cdot a_0"),
            ("ka", r"k\cdot a"),
            ("kh_0", r"k\cdot h_0"),
            ("kH_0", r"k\cdot H_0"),
            ("kV_0", r"k\cdot V_0"),
            ("kV_p", r"k\cdot V_p"),
            ("kV_0", r"k\cdot V_0"),
        ):
            formula = formula.replace(old, new)
        for name, amount in sorted(variables.items(), key=lambda item: -len(item[0])):
            formula = re.sub(
                r"(?<![A-Za-z_\\])" + re.escape(name) + r"(?![A-Za-z_0-9])",
                lambda _, v=amount: "(" + sp.latex(sp.sympify(v)) + ")",
                formula,
            )
        try:
            values = [PiParser(v).parse().value for v in formula.split("=")]
        except UnsupportedCondition as exc:
            raise AssertionError((m.kind, formula)) from exc
        assert len(values) > 1 and all(
            sp.simplify(v - values[0]) == 0 for v in values
        ), (m.kind, formula)
    assert sp.simplify(PiParser(result.answer).parse().value - expected) == 0, (
        m.kind,
        result.answer,
        expected,
    )
