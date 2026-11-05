"""Independent convex sections and reflected-apex intersections verify the proofs."""

import sympy as sp
from altitude_geometry_oracle import scalar, substitute
from bs4 import BeautifulSoup
from plane_geometry_oracle import foot
from section_geometry_oracle import area


def vertical(m):
    a, e = (dict(m.given)[n] for n in ("a", "e"))
    v = sp.sqrt(3) * a / 2
    h = sp.sqrt(e * e - a * a / 3)
    A = sp.Matrix([-a / 2, 0, 0])
    B = sp.Matrix([a / 2, 0, 0])
    C = sp.Matrix([0, v, 0])
    O = sp.Matrix([0, v / 3, 0])
    S = O + sp.Matrix([0, 0, h])
    M = (S + A) / 2
    N = (S + B) / 2
    K = (M + N) / 2
    L = sp.Matrix([K[0], K[1], 0])
    ratio = sp.simplify((C[1] - L[1]) / v)
    P = C + ratio * (A - C)
    Q = C + ratio * (B - C)
    normal = (N - M).cross(P - M)
    assert sp.simplify(normal[2]) == 0
    assert sp.simplify(normal.dot(Q - M)) == 0
    E = (A + B) / 2
    assert sp.simplify((C - L).norm() / (L - E).norm()) == 5
    points = {"A": A, "B": B, "C": C, "S": S, "O": O, "M": M, "N": N, "K": K}
    left = m.symbols.get("lower_left", "P")
    right = m.symbols.get("lower_right", "Q")
    points.update({m.names[0]: E, m.symbols.get("foot", "L"): L, left: P, right: Q})
    answer = area(M, N, Q) + area(M, Q, P)
    return points, {"S_{MN" + right + left + "}": answer}, answer


def reflected(m):
    a = m.given[0][1]
    square = m.mode == "reflected_square_section_midline"
    if square:
        h = a / sp.sqrt(2)
        A = sp.Matrix([-a / 2, -a / 2, 0])
        B = sp.Matrix([a / 2, -a / 2, 0])
        C = sp.Matrix([a / 2, a / 2, 0])
        D = sp.Matrix([-a / 2, a / 2, 0])
        S = sp.Matrix([0, 0, h])
        M = (S + A) / 2
        L = B + (C - B) / 3
        P = A + (D - A) / 3
        K = (S + B) / 2
        points = {"A": A, "B": B, "C": C, "D": D}
    else:
        h = a * sp.sqrt(sp.Rational(2, 3))
        B = sp.Matrix([0, a / sp.sqrt(3), 0])
        C = sp.Matrix([-a / 2, -a / (2 * sp.sqrt(3)), 0])
        D = sp.Matrix([a / 2, -a / (2 * sp.sqrt(3)), 0])
        S = sp.Matrix([0, 0, h])
        M = (S + B) / 2
        L = C + sp.Rational(7, 9) * (D - C)
        P = C + sp.Rational(7, 9) * (B - C)
        K = (S + D) / 2
        points = {"B": B, "C": C, "D": D, "B_1": (C + D) / 2}
    S1 = -S
    T = S1 + sp.Rational(2, 3) * (M - S1)
    points.update(S=S, S_1=S1, T=T, O=sp.zeros(3, 1), M=M, L=L, P=P, K=K)
    normal = (L - S1).cross(M - S1)
    for p in (P, K):
        assert sp.simplify(normal.dot(p - S1)) == 0
    assert sp.simplify((L - P).cross(K - M).norm()) == 0
    assert sp.simplify((M - P).norm() - (K - L).norm()) == 0
    answer = sp.simplify(((L - P).norm() + (K - M).norm()) / 2)
    return points, {"l": answer}, answer


def median(m):
    a, e = (dict(m.given)[n] for n in ("a", "e"))
    h = sp.sqrt(e * e - a * a / 2)
    A = sp.Matrix([-a / 2, -a / 2, 0])
    B = sp.Matrix([a / 2, -a / 2, 0])
    C = sp.Matrix([a / 2, a / 2, 0])
    D = sp.Matrix([-a / 2, a / 2, 0])
    M = sp.Matrix([0, 0, h])
    E = (M + D) / 2
    P = (M + B + D) / 3
    F = M + sp.Rational(2, 3) * (A - M)
    G = M + sp.Rational(2, 3) * (C - M)
    normal = (E - B).cross(F - B)
    assert sp.simplify(normal.dot(G - B)) == 0
    assert sp.simplify((M - C).dot(D - B)) == 0
    assert sp.simplify((E - B).dot(G - F)) == 0
    f = m.symbols.get("on_MA", "F")
    g = m.symbols.get("on_MC", "G")
    points = {
        "A": A,
        "B": B,
        "C": C,
        "D": D,
        "M": M,
        "E": E,
        "P": P,
        "O": sp.zeros(3, 1),
        f: F,
        g: G,
    }
    answer = area(B, F, E) + area(B, E, G)
    boundary = "B" + (g + "E" + f if m.names[0] == "point" else f + "E" + g)
    return points, {"S_{" + boundary + "}": answer}, answer


def perpendicular(m):
    e, a = (dict(m.given)[n] for n in ("e", "a"))
    r = a / sp.sqrt(3)
    h = sp.sqrt(e * e - r * r)
    A = sp.Matrix([r, 0, 0])
    B = sp.Matrix([-r / 2, a / 2, 0])
    C = sp.Matrix([-r / 2, -a / 2, 0])
    S = sp.Matrix([0, 0, h])
    K = foot(B, C, S)
    assert sp.simplify((A - K).dot(S - C)) == 0
    parameter = sp.simplify((K - C).dot(S - C) / (S - C).dot(S - C))
    assert 0 < parameter <= 1
    answer = area(A, B, K)
    volume = sp.simplify(abs(sp.det(sp.Matrix.hstack(B - A, C - A, S - A))) / 6)
    assert sp.simplify(3 * volume / e - answer) == 0
    return (
        {"A": A, "B": B, "C": C, "S": S, "K": K, "O": sp.zeros(3, 1)},
        {"Q": answer, "V": volume, r"S_{ABC}": area(A, B, C)},
        answer,
    )


def adjacent(m):
    a, e = (dict(m.given)[n] for n in ("a", "e"))
    h = sp.sqrt(e * e - a * a / 2)
    A, B = sp.Matrix([0, 0, 0]), sp.Matrix([a, 0, 0])
    C, D = sp.Matrix([a, a, 0]), sp.Matrix([0, a, 0])
    O = (A + C) / 2
    S = O + sp.Matrix([0, 0, h])
    X, Y = (A + B) / 2, (B + C) / 2
    F = (X + Y) / 2
    x, y, f = (
        m.symbols.get(k, v)
        for k, v in (("on_AB", "K"), ("on_BC", "M"), ("height_foot", "P"))
    )
    assert sp.simplify((S - F).dot(Y - X)) == 0
    assert sp.simplify((S - D).dot(Y - X)) == 0
    assert sp.simplify((D - F).norm() / (B - F).norm()) == 3
    small = area(B, X, Y)
    assert sp.simplify(small / (a * a - small)) == sp.Rational(1, 7)
    answer = area(S, X, Y)
    return (
        {"A": A, "B": B, "C": C, "D": D, "S": S, "O": O, x: X, y: Y, f: F},
        {
            "S_{ABCD}": a * a,
            "S_{B" + y + x + "}": small,
            "S_{" + x + "ADC" + y + "}": a * a - small,
            "V_{SB" + y + x + "}": small * h / 3,
            "V_{S" + x + "ADC" + y + "}": (a * a - small) * h / 3,
            "S_{S" + x + y + "}": answer,
        },
        answer,
    )


def vertical_vertex(m):
    a, e, am, sk = (dict(m.given)[k] for k in ("a", "e", "AM", "SK"))
    A, B = sp.Matrix([a, 0, 0]), sp.zeros(3, 1)
    C, D = sp.Matrix([0, a, 0]), sp.Matrix([a, a, 0])
    O = (A + C) / 2
    S = O + sp.Matrix([0, 0, sp.sqrt(e * e - a * a / 2)])
    M, K = A + am / a * (B - A), S + sk / e * (B - S)
    F = sp.Matrix([K[0], K[1], 0])
    normal = (K - M).cross(F - M)
    assert normal[2] == 0 and sp.simplify(normal.dot(C - M)) == 0
    sides = [sp.simplify(normal.dot(P - M)) for P in (A, D, S, B)]
    assert all(sides[i] * sides[0] > 0 for i in (1, 2)) and sides[3] * sides[0] < 0
    assert sp.simplify((F - B).cross(D - B).norm()) == 0
    assert sp.simplify((F - M).cross(C - M).norm()) == 0
    assert sp.simplify((K - F).dot(C - M)) == 0
    points = {"A": A, "B": B, "C": C, "D": D, "O": O, "S": S, "M": M, "K": K}
    if m.symbols.get("method") == "coincident_feet":
        points.update(H=F, H_1=F)
    else:
        points.update(L=F, H=C, N=C)
    answer = area(M, K, C)
    return points, {"S_{MKC}": answer}, answer


def geometry(m):
    if m.mode == "square_vertical_vertex_area":
        return vertical_vertex(m)
    if m.mode == "square_adjacent_midpoint_area":
        return adjacent(m)
    if m.mode == "triangle_vertical_section_area":
        return vertical(m)
    if m.mode.startswith("reflected_"):
        return reflected(m)
    if m.mode == "square_median_section_area":
        return median(m)
    return perpendicular(m)


def verify(html, m):
    points, extras, answer = geometry(m)
    values = {
        a + b: sp.simplify((p - q).norm())
        for a, p in points.items()
        for b, q in points.items()
        if a != b
    }
    values.update(extras)
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        raw = substitute(formula, values)
        sides = [scalar(side) for side in raw.split("=")]
        assert len(sides) > 1 and all(sp.simplify(v - sides[0]) == 0 for v in sides), (
            formula
        )
    return answer
