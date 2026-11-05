"""Independent right-pyramid coordinates check every displayed equality."""

import sympy as sp
from altitude_geometry_oracle import scalar, substitute
from bs4 import BeautifulSoup
from plane_geometry_oracle import foot
from section_geometry_oracle import area


def verify(html, m):
    a, e, t, be = (dict(m.given)[key] for key in ("a", "e", "AD", "BE"))
    A = sp.zeros(3, 1)
    B = sp.Matrix([a, 0, 0])
    C = sp.Matrix([a / 2, sp.sqrt(3) * a / 2, 0])
    h = sp.sqrt(e * e - a * a)
    M = sp.Matrix([0 if m.names[0] == "A" else a, 0, h])
    ma = (M - A).norm()
    al = ma - be if m.names[0] == "A" else ma / 2 if m.names[1] == "F" else t
    P = A + al / ma * (M - A)
    D = A + t / a * (C - A)
    E = A + (a - be) / a * (B - A)
    normal = (P - D).cross(E - D)
    signs = [sp.simplify(normal.dot(V - D)) for V in (A, B, C, M)]
    assert (
        signs[0] * signs[1] < 0 and signs[1] * signs[2] > 0 and signs[1] * signs[3] > 0
    )
    p = m.names[1]
    points = {"A": A, "B": B, "C": C, "M": M, "D": D, "E": E, p: P}
    if p == "F":
        K = (A + B) / 2
        N = foot(K, D, E)
        assert sp.simplify((P - N).dot(E - D)) == 0
        points.update(K=K, N=N)
    else:
        points["H"] = foot(P, D, E) if m.names[0] == "A" else foot(E, P, D)
    answer = area(P, D, E)
    values = {
        x + y: sp.simplify((X - Y).norm())
        for x, X in points.items()
        for y, Y in points.items()
        if x != y
    }

    def cosine(X, O, Y):
        return sp.simplify((X - O).dot(Y - O) / ((X - O).norm() * (Y - O).norm()))

    values.update(
        {
            r"\cos\angle CAM": cosine(C, A, M),
            r"\cos\angle MAB": cosine(M, A, B),
            r"\cos\angle " + p + "ED": cosine(P, E, D),
            r"\sin\angle " + p + "ED": sp.simplify(
                (P - E).cross(D - E).norm() / ((P - E).norm() * (D - E).norm())
            ),
            r"\sin60^\circ": sp.sqrt(3) / 2,
            "p": sp.simplify(((P - D).norm() + (P - E).norm() + (D - E).norm()) / 2),
            "S_{D" + p + "E}": answer,
            "S_{LDE}": answer,
        }
    )
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        raw = substitute(formula, values)
        sides = [scalar(side) for side in raw.split("=")]
        assert len(sides) > 1 and all(sp.simplify(v - sides[0]) == 0 for v in sides), (
            formula
        )
    return answer
