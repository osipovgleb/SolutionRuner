"""Check cone formulas with independent dimensions, exact π and physical scale ratios."""

import re

import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import solution_html
from sphere_formula_oracle import PiParser


def quantities(m):
    if m.mode == "similarity":
        a = m.given[0]
        k = m.ratio
        if len(m.given) == 3:
            k = m.given[1] / (m.given[1] + m.given[2])
        if m.kind == "liquid":
            return {
                "k": k,
                "h_0": sp.S.One,
                "h_1": k,
                "V_0": a / k**3,
                "V_1": a,
                r"\Delta V": a / k**3 - a,
            }
        power = 3 if m.kind == "volume" else 2
        symbol = "V" if m.kind == "volume" else "S"
        return {
            "k": k,
            "h_0": sp.S.One,
            "h_1": k,
            symbol + "_0": a,
            symbol + "_1": a * k**power,
        }
    if m.mode == "scale":
        k = m.ratio
        r1 = sp.S.One
        r2 = k if m.input_kind == "radius" else r1
        if m.kind == "volume":
            h1 = sp.S.One
            h2 = k if m.input_kind == "height" else h1
            l1 = sp.sqrt(r1 * r1 + h1 * h1)
            l2 = sp.sqrt(r2 * r2 + h2 * h2)
        else:
            l1 = 2 * max(sp.S.One, 1 / k)
            l2 = l1 * k if m.input_kind == "slant" else l1
            h1 = sp.sqrt(l1 * l1 - r1 * r1)
            h2 = sp.sqrt(l2 * l2 - r2 * r2)
        return {
            "r_1": r1,
            "r_2": r2,
            "h_1": h1,
            "h_2": h2,
            "l_1": l1,
            "l_2": l2,
            "V_1": sp.pi * r1 * r1 * h1 / 3,
            "V_2": sp.pi * r2 * r2 * h2 / 3,
            "S_1": sp.pi * r1 * l1,
            "S_2": sp.pi * r2 * l2,
        }
    a, b = m.given
    if m.input_kind == "height_slant":
        h, l = a, b
        r = sp.sqrt((l - h) * (l + h))
    elif m.input_kind == "height_diameter":
        h, r = a, b / 2
        l = sp.sqrt(h * h + r * r)
    elif m.input_kind == "diameter_slant":
        r, l = a / 2, b
        h = sp.sqrt((l - r) * (l + r))
    elif m.input_kind == "radius_height":
        r, h = a, b
        l = sp.sqrt(h * h + r * r)
    elif m.input_kind == "base_height":
        r, h = sp.sqrt(a / sp.pi), b
        l = sp.sqrt(h * h + r * r)
    elif m.input_kind == "circumference_slant":
        r, l = a / (2 * sp.pi), b
        h = sp.sqrt(l * l - r * r)
    elif m.input_kind == "slant_angle":
        l, h, r = a, a / 2, a * sp.sqrt(3) / 2
    else:
        r = h = a / 2 if m.input_kind == "diameter_apex" else a
        l = sp.sqrt(2) * r
    assert sp.simplify(l * l - r * r - h * h) == 0
    return {
        "r": r,
        "h": h,
        "l": l,
        "d": 2 * r,
        "B": sp.pi * r * r,
        "C": 2 * sp.pi * r,
        "A": r * h,
        "V": sp.pi * r * r * h / 3,
        "S": sp.pi * r * l if m.kind == "lateral" else sp.pi * r * (r + l),
        r"\alpha": sp.Integer(45),
    }


def verify(result, m):
    variables = quantities(m)
    nodes = BeautifulSoup(solution_html(result), "html.parser").select(
        "[data-inline-latex]"
    )
    assert 5 <= len(nodes) <= 9
    for node in nodes:
        f = node["data-inline-latex"].replace(r"^\circ", "")
        for old, new in [
            ("r_1^2h_1", r"r_1^2\cdot h_1"),
            ("r_2^2h_2", r"r_2^2\cdot h_2"),
            ("r_1l_1", r"r_1\cdot l_1"),
            ("r_2l_2", r"r_2\cdot l_2"),
            ("r^2h", r"r^2\cdot h"),
            ("rl", r"r\cdot l"),
            ("Cl", r"C\cdot l"),
            ("rh", r"r\cdot h"),
        ]:
            f = f.replace(old, new)
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
    answer = PiParser(result.answer).parse().value
    if m.mode == "geometry":
        expected = variables[
            {
                "volume": "V",
                "total": "S",
                "slant": "l",
                "height": "h",
                "diameter": "d",
                "axial": "A",
                "lateral": "S",
            }[m.kind]
        ] / (sp.pi if m.kind in {"volume", "total"} else 1)
    elif m.mode == "similarity":
        expected = (
            variables[r"\Delta V"]
            if m.kind == "liquid"
            else variables["V_1" if m.kind == "volume" else "S_1"]
        )
    else:
        symbol = "V" if m.kind == "volume" else "S"
        expected = variables[symbol + "_2"] / variables[symbol + "_1"]
        expected = expected if m.ratio > 1 else 1 / expected
    assert sp.simplify(answer - expected) == 0
