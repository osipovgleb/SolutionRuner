"""Coordinates, cross products and tetrahedral determinants check section proofs."""

import re

import sympy as sp
from altitude_geometry_oracle import point_plane, scalar, substitute
from bs4 import BeautifulSoup
from plane_geometry_oracle import foot


def cosine(points, name):
    a, b, c = (points[n] for n in name)
    u, v = a - b, c - b
    return sp.simplify(u.dot(v) / (u.norm() * v.norm()))


def area(a, b, c):
    return sp.simplify((b - a).cross(c - a).norm() / 2)


def cube(m):
    a, p, b = (dict(m.given)[k] for k in ("a", "p", "b"))
    vertical = m.mode == "cube_vertical_plane_distance"
    points = {
        "A": sp.Matrix([a, 0, 0]),
        "B": sp.zeros(3, 1),
        "C": sp.Matrix([0, a, 0]),
        "D": sp.Matrix([a, a, 0]),
    }
    points.update({n + "_1": v + sp.Matrix([0, 0, a]) for n, v in list(points.items())})
    A, B, C, D = (points[n] for n in "ABCD")
    P = D + sp.Matrix([0, 0, p]) if vertical else D + p / a * (C - D)
    Q = B + sp.Matrix([0, 0, a - b])
    base = points["A_1"] if vertical else A
    normal = (P - base).cross(Q - base)
    z = sp.simplify(-normal.dot(C - base) / normal[2])
    M = C + sp.Matrix([0, 0, z])
    assert sp.simplify(z - a / 2) == 0
    points.update(P=P, Q=Q, M=M)
    if vertical:
        points.update(
            K=(A + C) / 2, N=(points["A_1"] + points["C_1"]) / 2, O=(P + Q) / 2
        )
        origin = points["C_1"]
        u, v, w = P, Q, M
        extras = {r"S_{QMC_1}": area(Q, M, origin), r"S_{PQM}": area(P, Q, M)}
    else:
        t = -A[0] / (P[0] - A[0])
        R = A + t * (P - A)
        points["R"] = R
        origin = C
        u, v, w = P, R, M
        extras = {r"S_{MPC}": area(M, P, C), r"S_{RPM}": area(R, P, M)}
    extras["V"] = sp.simplify(
        abs(sp.det(sp.Matrix.hstack(u - origin, v - origin, w - origin))) / 6
    )
    independent = point_plane(origin, base, P, Q)
    assert sp.simplify(3 * extras["V"] / area(u, v, w) - independent) == 0
    return points, extras, independent


def parallel(m):
    a, d, e, t = (dict(m.given)[n] for n in ("a", "d", "e", "t"))
    b = sp.sqrt(d * d - a * a)
    h = sp.sqrt(e * e - d * d / 4)
    A = sp.Matrix([-a / 2, -b / 2, 0])
    B = sp.Matrix([a / 2, -b / 2, 0])
    C = sp.Matrix([a / 2, b / 2, 0])
    D = sp.Matrix([-a / 2, b / 2, 0])
    S = sp.Matrix([0, 0, h])
    E = B + t / d * (D - B)
    F = S + t / e * (A - S)
    normal = (E - C).cross(F - C)
    assert sp.simplify(normal.dot(B - S)) == 0
    r = sp.simplify(-normal.dot(D - C) / normal.dot(S - D))
    Q = D + r * (S - D)
    u = sp.simplify((A[1] - C[1]) / (E[1] - C[1]))
    M = C + u * (E - C)
    H = sp.Matrix([Q[0], Q[1], 0])
    assert all(sp.simplify((S - p).norm() - e) == 0 for p in (A, B, C, D))
    assert sp.simplify((B - D).norm() - d) == 0
    return (
        {
            "A": A,
            "B": B,
            "C": C,
            "D": D,
            "S": S,
            "E": E,
            "F": F,
            "Q": Q,
            "M": M,
            "H": H,
            "O": sp.zeros(3, 1),
        },
        {},
        sp.simplify(Q[2]),
    )


def bisector(m):
    given = m.given[0][1]
    a = given if m.mode.endswith("area") else sp.sqrt(4 * given / sp.sqrt(3))
    e = (1 + sp.sqrt(5)) * a / 2
    r = a / sp.sqrt(3)
    h = sp.sqrt(e * e - r * r)
    A = sp.Matrix([r, 0, 0])
    B = sp.Matrix([-r / 2, a / 2, 0])
    C = sp.Matrix([-r / 2, -a / 2, 0])
    S = sp.Matrix([0, 0, h])
    fraction = (S - A).norm() / ((S - A).norm() + (C - A).norm())
    M = sp.simplify(S + fraction * (C - S))
    points = {"A": A, "B": B, "C": C, "S": S, "M": M}
    assert sp.simplify((M - A).norm() - a) == 0
    assert sp.simplify((M - B).norm() - a) == 0
    actual = area(A, M, B)
    if m.mode.endswith("edge"):
        assert sp.simplify(actual - given) == 0
    angles = {}
    for name, degrees in (("SAC", 72), ("SCA", 72), ("MAC", 36), ("AMC", 72)):
        assert sp.simplify(cosine(points, name) - sp.cos(sp.pi * degrees / 180)) == 0
        angles[r"\angle " + name] = degrees
    return (
        points,
        angles | {r"S_{AMB}": actual},
        actual if m.mode.endswith("area") else a,
    )


def trapezoid(m):
    a = m.given[0][1]
    h = sp.sqrt(a * a - a * a / 2)
    A = sp.Matrix([-a / 2, -a / 2, 0])
    B = sp.Matrix([a / 2, -a / 2, 0])
    C = sp.Matrix([a / 2, a / 2, 0])
    D = sp.Matrix([-a / 2, a / 2, 0])
    P = sp.Matrix([0, 0, h])
    K = (A + P) / 2
    L = (A + B) / 2
    M = (C + D) / 2
    N = (P + D) / 2
    normal = (L - K).cross(M - K)
    assert sp.simplify(normal.dot(N - K)) == 0
    assert sp.simplify(normal.dot(B - P)) == 0
    assert sp.simplify(normal.dot(C - B)) == 0
    actual = area(K, L, M) + area(K, M, N)
    points = {
        "A": A,
        "B": B,
        "C": C,
        "D": D,
        "P": P,
        "K": K,
        "L": L,
        "M": M,
        "N": N,
        "O": sp.zeros(3, 1),
    }
    if m.mode.endswith("angle"):
        points.update(G=L, F=M, E=N, N=(B + C) / 2)
        cos = sp.simplify(abs(normal[2]) / normal.norm())
        assert sp.simplify(cosine(points, "PNO") - cos) == 0
        return points, {}, sp.acos(cos)
    points["F"] = foot(K, L, M)
    return points, {r"S_{KLMN}": actual}, actual


def geometry(m):
    if m.mode.startswith("cube_"):
        return cube(m)
    if m.mode == "pyramid_parallel_section_height":
        return parallel(m)
    if m.mode.startswith("triangle_bisector_"):
        return bisector(m)
    return trapezoid(m)


def verify(html, m):
    points, extras, answer = geometry(m)
    values = {
        a + b: sp.simplify((p - q).norm())
        for a, p in points.items()
        for b, q in points.items()
        if a != b
    }
    values.update(extras, h=answer)
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        if formula.startswith(r"\angle PNO="):
            assert formula == r"\angle PNO=" + sp.latex(answer, inv_trig_style="full")
            continue

        def trig(match):
            cos = cosine(points, match[3])
            number = cos if match[1] == "cos" else sp.sqrt(1 - cos * cos)
            return "(" + sp.latex(sp.simplify(number ** int(match[2] or 1))) + ")"

        formula = re.sub(
            r"\\(sin|cos)(?:\^(\d))?\s*\\angle\s*([A-Z]{3})", trig, formula
        )
        evaluations = [values]
        if re.search(r"\b[xyz]\b", formula):
            names = (
                ("A_1", "P", "Q", "M")
                if m.mode == "cube_vertical_plane_distance"
                else ("A", "P", "Q", "M")
            )
            evaluations = [
                values | dict(zip("xyz", points[n], strict=True)) for n in names
            ]
        for data in evaluations:
            raw = substitute(formula, data)
            sides = [scalar(side) for side in raw.split("=")]
            assert len(sides) > 1 and all(
                sp.simplify(v - sides[0]) == 0 for v in sides
            ), formula
    return answer
