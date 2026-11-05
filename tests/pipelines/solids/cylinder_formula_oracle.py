"""Check the physical dimensions and every published equality with exact pi."""

import re

import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import solution_html
from sphere_formula_oracle import PiParser


def quantities(m):
    if m.mode == "displacement":
        v, h, delta = m.given
        base = v / h
        return {
            "V_0": v,
            "h_0": h,
            r"\Delta h": delta,
            "B": base,
            "V_1": v + base * delta,
            "V": base * delta,
        }
    if m.mode == "transfer":
        h, k = m.given
        return {
            "h_1": h,
            "h_2": h / (k * k),
            "d_1": sp.Integer(2),
            "d_2": 2 * k,
            "V": sp.pi * h,
        }
    if m.mode == "volume_ratio":
        v, kh, kr = m.given
        return {
            "V_1": v,
            "V_2": v * kr * kr * kh,
            "R_1": sp.Integer(1),
            "R_2": kr,
            "H_1": v / sp.pi,
            "H_2": v / sp.pi * kh,
        }
    if m.mode == "axial_lateral":
        r, h = m.given[0] / 2, sp.Integer(1)
    elif m.mode == "lateral":
        first, h = m.given
        r = first if m.kind == "radius" else first / (2 * sp.pi)
    elif m.mode == "height":
        if m.kind == "diameter":
            s, d = m.given
            r = d / 2
            h = s / (sp.pi * d)
        else:
            c, s = m.given
            r = c / (2 * sp.pi)
            h = s / c
    else:
        s, h = m.given
        r = s / (2 * sp.pi * h)
    return {
        "r": r,
        "h": h,
        "d": 2 * r,
        "C": 2 * sp.pi * r,
        "S": 2 * sp.pi * r * h,
        "A": 2 * r * h,
    }


def verify(result, m):
    nodes = BeautifulSoup(solution_html(result), "html.parser").select(
        "[data-inline-latex]"
    )
    assert 5 <= len(nodes) <= 9
    variables = quantities(m)
    for node in nodes:
        f = node["data-inline-latex"]
        for old, new in (
            ("Ch", r"C\cdot h"),
            ("Bh_0", r"B\cdot h_0"),
            (r"B\Delta h", r"B\cdot \Delta h"),
            ("rh", r"r\cdot h"),
            ("dh", r"d\cdot h"),
        ):
            f = f.replace(old, new)
        f = re.sub(r"(?<=\d)(?=\\frac)", lambda _: r"\cdot", f)
        for name, amount in sorted(variables.items(), key=lambda p: -len(p[0])):
            f = re.sub(
                r"(?<![A-Za-z_\\])" + re.escape(name) + r"(?![A-Za-z_0-9])",
                lambda _, v=amount: "(" + sp.latex(v) + ")",
                f,
            )
        f = f.replace(r"\pi", r"(\pi)")
        values = [PiParser(v).parse().value for v in f.split("=")]
        assert len(values) > 1 and all(
            sp.simplify(v - values[0]) == 0 for v in values
        ), f
    assert sp.simplify(PiParser(result.answer).parse().value - m.answer) == 0
