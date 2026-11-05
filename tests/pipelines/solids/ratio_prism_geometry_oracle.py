"""Independent affine cuts and metric sections verify the complete proofs."""

import re

import sympy as sp
from altitude_geometry_oracle import scalar, substitute
from bs4 import BeautifulSoup
from plane_geometry_oracle import foot
from section_geometry_oracle import area


def midline(m):
    given = [v for _, v in m.given]
    q = given[0] if len(given) == 1 else given[1] / given[0]
    S, A, B, C = (
        sp.Matrix([0, 0, 1]),
        sp.zeros(3, 1),
        sp.Matrix([1, 0, 0]),
        sp.Matrix([0, 1, 0]),
    )
    _, ab, sc, sa, bc, request = m.names
    points = {
        "S": S,
        "A": A,
        "B": B,
        "C": C,
        ab: (A + B) / 2,
        sc: (S + C) / 2,
        sa: (q * S + A) / (q + 1),
        bc: (B + q * C) / (q + 1),
    }
    T = (q * S - B) / (q - 1)
    points["R" if m.names[0] == "external" else "F"] = T
    assert sp.simplify((points[sa] - points[ab]).cross(T - points[ab]).norm()) == 0
    assert sp.simplify((points[bc] - points[sc]).cross(T - points[sc]).norm()) == 0
    normal = (points[sa] - points[ab]).cross(points[sc] - points[ab])
    assert sp.simplify(normal.dot(points[bc] - points[ab])) == 0
    answer = q if request != "CN/NB" else 1 / q
    return points, {}, sp.simplify(answer)


def inverse(m):
    a, Q = (dict(m.given)[k] for k in ("a", "area"))
    h = sp.sqrt((a * a / 2) * 4 * Q * Q / (a**4 - 4 * Q * Q))
    D, A, C, B = (
        sp.zeros(3, 1),
        sp.Matrix([a, 0, 0]),
        sp.Matrix([0, a, 0]),
        sp.Matrix([a, a, 0]),
    )
    O = (A + C) / 2
    S = O + sp.Matrix([0, 0, h])
    H = foot(O, S, C)
    assert sp.simplify((B - H).dot(C - S)) == 0 and sp.simplify((D - H).dot(C - S)) == 0
    assert sp.simplify(area(B, H, D) - Q) == 0
    answer = sp.simplify((S - H).norm() / (H - C).norm())
    return (
        {"A": A, "B": B, "C": C, "D": D, "O": O, "S": S, "H": H},
        {"S_{BHD}": Q, "h": h},
        answer,
    )


def prism(m):
    a, h = (dict(m.given)[k] for k in ("a", "height"))
    A = sp.zeros(3, 1)
    B = sp.Matrix([a, 0, 0])
    C = sp.Matrix([a / 2, sp.sqrt(3) * a / 2, 0])
    up = sp.Matrix([0, 0, h])
    floor = {"A": A, "B": B, "C": C}
    end = m.names[1][1]
    opposite = "C" if end == "B" else "B"
    left, right = ("N", "K") if m.names[0] == "construct" else ("M", "N")
    P = (A + floor[opposite]) / 2 + up
    Q = (floor[end] + floor[opposite]) / 2 + up
    normal = (floor[end] - A).cross(P - A)
    assert sp.simplify(normal.dot(Q - A)) == 0
    side = sp.simplify(normal.dot(floor[opposite] - A))
    assert side * sp.simplify(normal.dot(floor[opposite] + up - A)) > 0
    assert all(
        side * sp.simplify(normal.dot(floor[k] + up - A)) < 0 for k in ("A", end)
    )
    points = {
        **floor,
        **{k + m.symbols["top"]: v + up for k, v in floor.items()},
        left: P,
        right: Q,
        "H": foot(P, A, floor[end]),
    }
    section_area = area(A, floor[end], Q) + area(A, Q, P)
    perimeter = sp.simplify(
        (floor[end] - A).norm()
        + (Q - floor[end]).norm()
        + (P - Q).norm()
        + (A - P).norm()
    )
    boundary = "ABKN" if m.names[0] == "construct" else "A" + left + right + end
    return (
        points,
        {"S_{" + boundary + "}": section_area, "P_{" + boundary + "}": perimeter},
        section_area if m.mode.endswith("area") else perimeter,
    )


def _coordinates(formula, points, extras):
    if formula.startswith(r"\overrightarrow{SC}="):
        raw = formula.split("=(", 1)[1][:-1]
        actual = sp.Matrix([scalar(substitute(v, extras)) for v in raw.split(";")])
        assert sp.simplify(actual - (points["C"] - points["S"])) == sp.zeros(3, 1)
        return True
    if formula.startswith(("D(", "O(")):
        for part in formula.split(r"\quad"):
            match = re.fullmatch(r"([ABCDOS])\((.*)\)", part.strip().strip(","))
            assert match, formula
            actual = sp.Matrix(
                [scalar(substitute(v, extras)) for v in match[2].split(";")]
            )
            assert sp.simplify(actual - points[match[1]]) == sp.zeros(3, 1)
        return True
    if "x+" in formula:
        for key in ("D", "B", "O", "H"):
            P = points[key]
            values = {**extras, "x": P[0], "y": P[1], "z": P[2]}
            assert scalar(substitute(formula.split("=")[0], values)) == 0
        P = points["S"]
        values = {**extras, "x": P[0], "y": P[1], "z": P[2]}
        assert scalar(substitute(formula.split("=")[0], values)) != 0
        return True
    return False


def _parallel(formula, points):
    names = formula.split(r"\parallel ")
    if len(names) == 1:
        return False
    vectors = []
    for name in names:
        tokens = re.findall(r"[ABC](?:_1|')?|[MNKH]", name)
        assert len(tokens) == 2 and "".join(tokens) == name
        vectors.append(points[tokens[1]] - points[tokens[0]])
    assert all(sp.simplify(vectors[0].cross(v).norm()) == 0 for v in vectors[1:])
    return True


def verify(html, m):
    if m.mode == "pyramid_midline_ratio":
        points, extras, answer = midline(m)
    elif m.mode == "square_perpendicular_section_ratio":
        points, extras, answer = inverse(m)
    else:
        points, extras, answer = prism(m)
    values = {
        a + b: sp.simplify((A - B).norm())
        for a, A in points.items()
        for b, B in points.items()
        if a != b
    }
    values.update(extras)
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        if m.mode == "square_perpendicular_section_ratio" and _coordinates(
            formula, points, extras
        ):
            continue
        if _parallel(formula, points):
            continue
        if formula == r"\frac{RM}{RN}=\frac{RK}{RL}":
            assert m.names[0] == "external" and "Предположим" in html
            assert values["RM"] / values["RN"] > 1 > values["RK"] / values["RL"]
            assert (
                sp.simplify(
                    (points["K"] - points["M"]).cross(points["L"] - points["N"]).norm()
                )
                != 0
            )
            continue
        sides = [scalar(side) for side in substitute(formula, values).split("=")]
        assert len(sides) > 1 and all(sp.simplify(v - sides[0]) == 0 for v in sides), (
            formula
        )
    return sp.simplify(answer)
