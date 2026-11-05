"""Check published equations using an independent coordinate and degree oracle."""

import re

import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import solution_html
from sphere_formula_oracle import PiParser


def points(m):
    base = {
        "hexagon": [
            (1, 0),
            (sp.Rational(1, 2), sp.sqrt(3) / 2),
            (-sp.Rational(1, 2), sp.sqrt(3) / 2),
            (-1, 0),
            (-sp.Rational(1, 2), -sp.sqrt(3) / 2),
            (sp.Rational(1, 2), -sp.sqrt(3) / 2),
        ],
        "triangle": [(0, 0), (1, 0), (sp.Rational(1, 2), sp.sqrt(3) / 2)],
        "cube": [(0, 0), (1, 0), (1, 1), (0, 1)],
        "square": [(0, 0), (1, 0), (1, 1), (0, 1)],
    }[m.body]
    return {
        chr(65 + i) + ("_1" if z else ""): sp.Matrix((x, y, z * m.height_ratio))
        * m.edge
        for z in (0, 1)
        for i, (x, y) in enumerate(base)
    }


def angle(p, a, vertex, b):
    u, v = p[a] - p[vertex], p[b] - p[vertex]
    return sp.simplify(180 / sp.pi * sp.acos(u.dot(v) / sp.sqrt(u.dot(u) * v.dot(v))))


def verify(result, m):
    p = points(m)

    def length(a, b):
        v = p[a] - p[b]
        return sp.sqrt(sp.simplify(v.dot(v)))

    values = {
        "a": m.edge,
        "R": m.edge,
        "n": sp.Integer(6),
        r"\gamma": sp.Integer(120),
        r"\alpha": sp.Integer(60),
        r"\beta": sp.Integer(60),
        r"\theta": m.answer,
        r"\varphi": sp.Integer(45),
        "d": m.edge * (sp.sqrt(2) if m.body == "cube" else 2),
    }
    for a in p:
        for b in p:
            if a != b:
                values[a + b] = length(a, b)
    html = BeautifulSoup(solution_html(result), "html.parser")
    rows = html.select("center [data-inline-latex]")
    assert 5 <= len(rows) <= 9
    for node in rows:
        formula = node["data-inline-latex"]
        if r"\parallel" in formula:
            a, b = formula.split(r"\parallel ")
            aa, ab = re.findall(r"[A-F](?:_1)?", a)
            ba, bb = re.findall(r"[A-F](?:_1)?", b)
            assert (p[ab] - p[aa]).cross(p[bb] - p[ba]) == sp.zeros(3, 1)
            continue
        for raw in re.findall(r"\\(?:tg\\angle |angle )((?:[A-F](?:_1)?){3})", formula):
            a, v, b = re.findall(r"[A-F](?:_1)?", raw)
            degree = angle(p, a, v, b)
            formula = formula.replace(
                r"\tg\angle " + raw, "(" + sp.latex(sp.tan(degree * sp.pi / 180)) + ")"
            )
            formula = formula.replace(r"\angle " + raw, "(" + sp.latex(degree) + ")")
        formula = (
            formula.replace(r"\cos120^{\circ}", r"(-\frac{1}{2})")
            .replace(r"\cos\alpha", r"\frac{1}{2}")
            .replace(r"^{\circ}", "")
        )
        for name, amount in sorted(values.items(), key=lambda item: -len(item[0])):
            formula = re.sub(
                r"(?<![A-Za-z_\\])" + re.escape(name) + r"(?![A-Za-z_0-9])",
                lambda _, v=amount: "(" + sp.latex(v) + ")",
                formula,
            )
        formula = re.sub(r"\)(?=\d)", r")\\cdot ", formula)
        results = [PiParser(v).parse().value for v in formula.split("=")]
        assert len(results) > 1 and all(
            sp.simplify(v - results[0]) == 0 for v in results
        ), formula
    assert "вектор" not in html.get_text().lower()
