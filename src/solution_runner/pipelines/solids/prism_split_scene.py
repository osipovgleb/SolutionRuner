"""Actual isosceles-prism midpoints, feet and reviewed affine cameras."""

import math
from copy import deepcopy

import sympy as sp

from ..core.errors import ContentPlanError
from . import projection_drawing as drawing
from .box_svg import _clear

PURPOSES = {"image_1": "geometric", "image_2": "vector", "image_3": "axes"}
EDGES = (
    ("A", "B"),
    ("B", "C"),
    ("C", "A"),
    ("A_1", "B_1"),
    ("B_1", "C_1"),
    ("C_1", "A_1"),
    ("A", "A_1"),
    ("B", "B_1"),
    ("C", "C_1"),
)


def points(m, purpose):
    a, b, h, t = (m.q[k] for k in ("a", "b", "height", "fraction"))
    v = m.q["base_height"]
    p = {"A": sp.zeros(3, 1), "B": sp.Matrix([b / 2, v, 0]), "C": sp.Matrix([b, 0, 0])}
    p.update({n + "_1": x + sp.Matrix([0, 0, h]) for n, x in list(p.items())})
    p.update(K=(p["A_1"] + p["B_1"]) / 2, N=(p["A"] + p["B"]) / 2, M=t * p["C"])
    if purpose == "geometric":
        p["H"] = p["B"] * (t * b * b / (2 * a * a))
        if m.names[0] == "quarter":
            p["E"], p["L"] = p["B"] * (b * b / (2 * a * a)), p["C"] / 2
    elif purpose == "vector":
        p.update(
            va=p["B"] + sp.Rational(7, 10) * (p["A"] - p["B"]),
            vb=p["B"] + sp.Rational(3, 4) * (p["C"] - p["B"]),
            vc=(p["B"] + p["B_1"]) / 2,
        )
    else:
        p.update(
            x=sp.Matrix([sp.Rational(33, 25) * b, 0, 0]),
            y=sp.Matrix([0, sp.Rational(14, 25) * v, 0]),
            z=sp.Matrix([0, 0, sp.Rational(127, 100) * h]),
        )
    return p


def template(m, slot):
    if slot not in PURPOSES:
        raise ContentPlanError("a reviewed prism illustration slot is required")
    purpose = PURPOSES[slot]
    meta = deepcopy(drawing.template("prism_split_" + purpose))
    if purpose == "geometric" and m.names[0] == "half":
        meta["discarded_groups"] = [meta["glyph_indices"].pop(n) for n in ("E", "L")]
        for n in ("E", "L"):
            del meta["glyph_boxes"][n]
    return purpose, meta


def marker(p, project, center, first, second, delta):
    foot = p[center]
    u, v = p[first] - foot, p[second] - foot
    if u.norm() == 0 or v.norm() == 0 or sp.simplify(u.dot(v)) != 0:
        raise ContentPlanError("the specified prism corner is not a right angle")
    u, v = u * (delta / float(u.norm())), v * (delta / float(v.norm()))
    result = [project(foot + z) for z in (u, u + v, v)]
    if (
        abs(
            (result[1][0] - result[0][0]) * (result[2][1] - result[1][1])
            - (result[1][1] - result[0][1]) * (result[2][0] - result[1][0])
        )
        < 0.4
    ):
        raise ContentPlanError("the projected right-angle mark collapses")
    return result


def scene(m, purpose, meta):
    p = points(m, purpose)
    names = [n for n in p if n[0].isupper()]
    if any(
        sp.simplify(p[a] - p[b]).is_zero_matrix for a in names for b in names if a < b
    ):
        raise ContentPlanError(
            "coincident prism helpers require a reviewed joint label"
        )
    failures = []
    cameras = (
        ((0.4, 1), (0.6, 1), *drawing.PROJECTIONS)
        if purpose == "geometric" and m.names[0] == "half"
        else drawing.PROJECTIONS
    )
    for factors in cameras:
        try:
            project, vertices = drawing.projector(p, meta, factors)
            if not _clear(
                {n: vertices[n] for n in ("A", "B", "C", "A_1", "B_1", "C_1")}, EDGES
            ):
                raise ContentPlanError("the prism wireframe is indistinct")
            if (
                min(
                    math.dist(vertices[a], vertices[b])
                    for a in names
                    for b in names
                    if a < b
                )
                < 6
            ):
                raise ContentPlanError("the prism helpers cannot be distinguished")
            delta = min(float(m.q[k]) for k in ("a", "b", "height")) * 0.06
            corners = []
            if purpose == "geometric":
                corners.append(("H", "M", "A"))
                if m.names[0] == "quarter":
                    corners.extend((("E", "C", "A"), ("L", "B", "C"), ("M", "N", "C")))
            elif m.names[0] == "quarter":
                corners.append(("M", "N", "C"))
            marks = [marker(p, project, *corner, delta) for corner in corners]
            return vertices, marks
        except ContentPlanError as exc:
            failures.append(exc)
    raise ContentPlanError(
        "the prism requires another reviewed projection"
    ) from failures[-1]
