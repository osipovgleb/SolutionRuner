"""Evaluate every published surface equality and both complete parent methods."""

import re

import sympy as sp
from bs4 import BeautifulSoup
from midpoint_source_cases import solution_html
from sphere_formula_oracle import PiParser
from test_orthogonal_geometry import voxel_measures

from solution_runner.pipelines.solids.orthogonal_surface_geometry import (
    bounding,
    central_cancellation,
    glued_parts,
    missing_box,
)

FIRST = "<p><b>Первый способ.</b></p>"
SECOND = "<p><b>Второй способ.</b></p>"


def variables(m, style):
    box = bounding(m)
    a, b, c = box.dimensions
    v = {
        "a": a,
        "b": b,
        "c": c,
        "S_0": box.surface,
        "S": voxel_measures(m.solid.additions, m.solid.cutouts)[1],
    }
    kind = style["method"]
    if kind in {"glued_two", "glued_three", "shelf_both"}:
        parts, shared = glued_parts(m, kind)
        v.update({"S_" + str(i): p.surface for i, p in enumerate(parts, 1)})
        x, y, z = (parts[0].dimensions[j] for j in style["orders"][0])
        v.update({"a_1": x, "b_1": y, "c_1": z, "A": shared})
        if kind == "shelf_both":
            tall, side = m.solid.additions
            gap = tall.dimensions[2] - side.dimensions[2]
            v.update(G=gap, B=side.dimensions[0] * gap)
        return v
    if kind == "cancel_central":
        central, parts, shared = central_cancellation(m)
        x, y, z = central.dimensions
        v.update(a=x, b=y, c=z, S_c=central.surface, A=shared)
        v.update({"S_" + str(i): p.surface for i, p in enumerate(parts, 1)})
        return v
    cut = missing_box(m)
    w, d, h = cut.dimensions
    v.update(w=w, d=d, h=h)
    if kind.startswith("reduced_"):
        v["B"] = {"reduced_xy": w * d, "reduced_xz": w * h, "reduced_yz": d * h}[kind]
    elif kind == "corner_grouped":
        v.update(H=2 * a * b, L=2 * b * c, F=2 * a * c)
    elif kind == "corner_nine":
        v.update(
            A_1=b * c + a * b + a * c,
            A_2=a * c - w * h + b * c - d * h + a * b - w * d,
            A_3=w * d + w * h + d * h,
        )
    elif kind in {"front_notch", "front_groove"}:
        v.update(
            A=d * (c if kind == "front_notch" else a),
            B=w * d if kind == "front_notch" else d * h,
        )
    elif kind == "hole_both":
        v.update(
            S_1=cut.surface,
            B=w * h,
            F=a * c - w * h,
            L=b * c,
            D=a * b,
            Q=w * b,
            R=h * b,
        )
    else:
        raise AssertionError((kind, "independent surface method missing"))
    return v


def verify(result, m, style):
    v = variables(m, style)
    html = solution_html(result)
    multi = style["method"] in {
        "corner_grouped",
        "corner_nine",
        "shelf_both",
        "hole_both",
    }
    blocks = html.removeprefix(FIRST).split(SECOND)
    assert len(blocks) == (2 if multi else 1)
    if multi:
        assert html.startswith(FIRST)
    pairs = {
        "ab": ("a", "b"),
        "ac": ("a", "c"),
        "bc": ("b", "c"),
        "wh": ("w", "h"),
        "wd": ("w", "d"),
        "dh": ("d", "h"),
        "wb": ("w", "b"),
        "hb": ("h", "b"),
        "a_1b_1": ("a_1", "b_1"),
        "a_1c_1": ("a_1", "c_1"),
        "b_1c_1": ("b_1", "c_1"),
    }
    for block in blocks:
        soup = BeautifulSoup(block, "html.parser")
        nodes = soup.select("[data-inline-latex]")
        paragraphs = [
            p for p in soup.find_all("p") if not p.select_one("[data-inline-latex]")
        ]
        assert 5 <= len(nodes) <= 9 and 2 <= len(paragraphs) <= 4
        for node in nodes:
            formula = node["data-inline-latex"]
            for pair, names in sorted(pairs.items(), key=lambda item: -len(item[0])):
                formula = re.sub(
                    r"(?<![A-Za-z_\\])" + re.escape(pair) + r"(?![A-Za-z_0-9])",
                    lambda _, ns=names: ns[0] + r"\cdot " + ns[1],
                    formula,
                )
            for name, amount in sorted(v.items(), key=lambda item: -len(item[0])):
                formula = re.sub(
                    r"(?<![A-Za-z_\\])" + re.escape(name) + r"(?![A-Za-z_0-9])",
                    lambda _, n=amount: "(" + sp.latex(n) + ")",
                    formula,
                )
            terms = [PiParser(part).parse().value for part in formula.split("=")]
            assert len(terms) >= 2 and all(
                sp.simplify(t - terms[0]) == 0 for t in terms
            ), (style, formula)
    assert PiParser(result.answer).parse().value == v["S"]
