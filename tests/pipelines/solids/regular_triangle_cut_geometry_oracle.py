"""Independent tetrahedral edge cuts and every equality in both parent methods."""

import sympy as sp
from altitude_geometry_oracle import scalar, substitute
from bs4 import BeautifulSoup
from section_geometry_oracle import area


def geometry(m):
    a, e, u = (v for _, v in m.given)
    t = u if m.given[2][0] == "AD" else a - u
    al = e - u
    A = sp.Matrix([a / sp.sqrt(3), 0, 0])
    B = sp.Matrix([-a / (2 * sp.sqrt(3)), a / 2, 0])
    C = sp.Matrix([-a / (2 * sp.sqrt(3)), -a / 2, 0])
    O = sp.zeros(3, 1)
    M = sp.Matrix([0, 0, sp.sqrt(e * e - a * a / 3)])
    D = A + t / a * (C - A)
    E = A + t / a * (B - A)
    L = A + al / e * (M - A)
    K = A + al / e * (O - A)
    H = (D + E) / 2
    normal = (D - L).cross(E - L)
    signs = [sp.simplify(normal.dot(P - D)) for P in (A, B, C, M)]
    assert all(signs[0] * v < 0 for v in signs[1:])
    assert sp.simplify((L - K).dot(O - A)) == 0
    assert sp.simplify((L - H).dot(D - E)) == 0
    if m.symbols["section_foot"] == "O":
        assert sp.simplify(H - O) == sp.zeros(3, 1)
    elif m.symbols["section_foot"] == "K":
        assert sp.simplify(H - K) == sp.zeros(3, 1) and H != O
    points = {"A": A, "B": B, "C": C, "M": M, "D": D, "E": E, "L": L, "K": K, "O": O}
    if m.symbols["section_foot"] == "H":
        points["H"] = H
    return points, area(D, L, E)


def verify(html, m):
    points, answer = geometry(m)
    values = {
        a + b: sp.simplify((A - B).norm())
        for a, A in points.items()
        for b, B in points.items()
        if a != b
    }
    A, B, M = (points[k] for k in ("A", "B", "M"))
    values.update(
        {
            "S_{DLE}": answer,
            r"\cos\angle BAM": sp.simplify(
                (B - A).dot(M - A) / ((B - A).norm() * (M - A).norm())
            ),
        }
    )
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        sides = [scalar(side) for side in substitute(formula, values).split("=")]
        assert len(sides) > 1 and all(sp.simplify(v - sides[0]) == 0 for v in sides), (
            formula
        )
    return answer
