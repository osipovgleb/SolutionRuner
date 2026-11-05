"""Independent coordinates for the projection and section proof equalities."""

import re

import sympy as sp
from bs4 import BeautifulSoup

from solution_runner.pipelines.equations.trig_parser import TrigonometricParser


def foot(p, a, b):
    v = b - a
    return a + (p - a).dot(v) / v.dot(v) * v


def prism(m):
    q = m.q
    a, b, c, _ = m.names
    points = {
        a: sp.Matrix([q["c"], 0, 0]),
        b: sp.Matrix([0, q["BC"], 0]),
        c: sp.zeros(3, 1),
    }
    points.update(
        {n + "_1": p + sp.Matrix([0, 0, q["H"]]) for n, p in list(points.items())}
    )
    points["E"] = foot(points[c], points[a], points[b])
    assert (
        sp.simplify((points[c] - points["E"]).dot(points[b + "_1"] - points["E"])) == 0
    )
    normal = (points[b] - points[a]).cross(sp.Matrix([0, 0, 1]))
    diagonal = points[c] - points[b + "_1"]
    actual_sine = abs(diagonal.dot(normal)) / (diagonal.norm() * normal.norm())
    assert sp.simplify(actual_sine - q["sin_beta"]) == 0
    angles = {b + a + c: q["a_angle"], b + "_1E" + c: 90, c + b + "_1E": q["beta"]}
    return points, angles, q["H"]


def square(m):
    a, h = m.q["a"], m.q["H"]
    points = {
        "A": sp.Matrix([-a / 2, -a / 2, 0]),
        "B": sp.Matrix([a / 2, -a / 2, 0]),
        "C": sp.Matrix([a / 2, a / 2, 0]),
        "D": sp.Matrix([-a / 2, a / 2, 0]),
        "M": sp.Matrix([0, 0, h]),
        "O": sp.zeros(3, 1),
    }
    A, B, C, D, M = (points[n] for n in "ABCDM")
    points["L"] = L = (B + M) / 2
    u, v = M - D, L - A
    assert sp.simplify(u.cross(v).norm() / abs(u.dot(v)) - m.q["tangent"]) == 0
    assert sp.simplify((C - A).cross(L - A).dot((D - M).cross(B - M))) == 0
    return points, {"alpha": sp.atan(m.q["tangent"]) * 180 / sp.pi}, h


def hexagon(m):
    a, h = m.q["a"], m.q["H"]
    points = {
        n: sp.Matrix([a * sp.cos(i * sp.pi / 3), a * sp.sin(i * sp.pi / 3), 0])
        for i, n in enumerate("ABCDEF")
    }
    points.update({n + "_1": p + sp.Matrix([0, 0, h]) for n, p in list(points.items())})
    y, z, w, plane = m.names
    P, Q, T = (points[n] for n in (y, z + "_1", w + "_1"))
    U, V, W = (points[n] for n in re.findall(r"[A-F](?:_1)?", plane))
    assert sp.simplify((Q - P).cross(T - P).dot((V - U).cross(W - U))) == 0
    if m.symbols.get("foot") == "upper":
        points["H"] = foot(P, Q, T)
    else:
        opposite = "ABCDEF"[("ABCDEF".index(y) + 3) % 6]
        points["H"] = foot(Q, P, points[opposite])
    distance = sp.simplify((P - Q).cross(T - Q).norm() / (T - Q).norm())
    return points, {}, distance


def tetrahedron(m):
    q = m.q
    a, e, h, r = (q[n] for n in ("a", "e", "H", "fraction"))
    radius = a / sp.sqrt(3)
    A = sp.Matrix([radius, 0, 0])
    B = sp.Matrix([-radius / 2, a / 2, 0])
    C = sp.Matrix([-radius / 2, -a / 2, 0])
    S = sp.Matrix([0, 0, h])
    K, M = A + r * (B - A), S + r * (C - S)
    on_sb = S + r * (B - S)
    on_ac = A + r * (C - A)
    H = (B + C) / 2
    R = A + r * (H - A)
    normal = (M - K).cross(on_sb - K)
    assert sp.simplify(normal.dot(S - A)) == 0
    assert sp.simplify(normal.dot(B - C)) == 0
    points = {
        "A": A,
        "B": B,
        "C": C,
        "S": S,
        "K": K,
        "M": M,
        "H": H,
        "O": sp.zeros(3, 1),
    }
    points[m.symbols.get("on_sb", "N")] = on_sb
    points[m.symbols.get("on_ac", "L")] = on_ac
    angles = {"SAO": sp.asin(h / e) * 180 / sp.pi}
    if m.mode == "ratio_plane_angle":
        face = (B - S).cross(C - S)
        cosine = sp.simplify(abs(normal.dot(face)) / (normal.norm() * face.norm()))
        angles["ASH"] = (
            sp.acos((A - S).dot(H - S) / ((A - S).norm() * (H - S).norm()))
            * 180
            / sp.pi
        )
        return points, angles, sp.acos(cosine)
    u, v = S - A, M - K
    distance = sp.simplify(abs((K - A).dot(u.cross(v))) / u.cross(v).norm())
    points.update(R=R, P=foot(R, A, S), E=R)
    assert sp.simplify((points["R"] - points["P"]).cross(normal).norm()) == 0
    return points, angles, distance


def geometry(m):
    return {
        "prism_projection_height": prism,
        "pyramid_skew_height": square,
        "hex_prism_distance": hexagon,
        "ratio_plane_distance": tetrahedron,
        "ratio_plane_angle": tetrahedron,
    }[m.mode](m)


def verify(html, m):
    points, angles, independent = geometry(m)
    values = {
        a + b: sp.simplify((p - q).norm())
        for a, p in points.items()
        for b, q in points.items()
        if a != b
    }
    values.update(a=m.q.get("a", 0), h=m.q["H"], x=m.q["H"], d=independent)
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        functions = {"sin": sp.sin, "cos": sp.cos, "tan": sp.tan}
        for angle, degrees in angles.items():
            pattern = r"\\alpha" if angle == "alpha" else r"\\angle\s*" + angle
            for name, function in functions.items():
                formula = re.sub(
                    r"\\" + name + r"\s*" + pattern,
                    lambda _, f=function, degrees=degrees: (
                        "(" + sp.latex(sp.simplify(f(degrees * sp.pi / 180))) + ")"
                    ),
                    formula,
                )
            formula = re.sub(
                pattern,
                lambda _, degrees=degrees: "(" + sp.latex(degrees) + ")",
                formula,
            )
        formula = re.sub(
            r"\\(sin|cos|tan)\s*(\d+)\^\{\\circ\}",
            lambda match, functions=functions: (
                "(" + sp.latex(functions[match[1]](sp.pi * int(match[2]) / 180)) + ")"
            ),
            formula,
        )
        formula = formula.replace(r"^{\circ}", "")
        # Inverse cosine is checked through the independently calculated angle.
        if formula.startswith(r"\varphi="):
            assert formula == r"\varphi=" + sp.latex(independent, inv_trig_style="full")
            continue
        formula = formula.replace(
            r"\cos\varphi", "(" + sp.latex(sp.cos(independent)) + ")"
        )
        formula = formula.replace(r"\tan", r"\tg")
        for symbol, number in sorted(values.items(), key=lambda pair: -len(pair[0])):
            formula = re.sub(
                r"(?<![A-Za-z_])" + re.escape(symbol) + r"(?![A-Za-z_])",
                lambda _, v=number: "(" + sp.latex(v) + ")",
                formula,
            )
        numbers = []
        for side in formula.split("="):
            reader = TrigonometricParser(side)
            expr = reader.parse().value
            numbers.append(sp.simplify(expr))
        assert len(numbers) > 1 and all(
            sp.simplify(n - numbers[0]) == 0 for n in numbers
        ), formula
    return independent
