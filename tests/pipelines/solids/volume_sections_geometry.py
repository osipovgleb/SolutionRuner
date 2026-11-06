"""Independent coordinate solids supply lengths, areas, volumes and median cuts."""

import sympy as sp
from projection_plane_equation_oracle import values_for


def area(a, b, c):
    return sp.simplify((b - a).cross(c - a).norm() / 2)


def volume(a, b, c, d):
    return sp.simplify(abs(sp.det(sp.Matrix.hstack(b - a, c - a, d - a))) / 6)


def hexagon(m):
    given = dict(m.given)
    a, e = given["a"], given["e"]
    p = {
        n: sp.Matrix([a * sp.sin(i * sp.pi / 3), a * sp.cos(i * sp.pi / 3), 0])
        for i, n in enumerate("ABCDEF")
    }
    p["S"] = sp.Matrix([0, 0, sp.sqrt(e * e - a * a)])
    p["M"] = (p["B"] + p["C"]) / 2
    extra = {}
    for name in ("SBE", "SBC"):
        A, B, C = (p[n] for n in name)
        u, v = A - B, C - B
        cosine = sp.simplify(u.dot(v) / (u.norm() * v.norm()))
        extra[r"\cos\angle " + name] = cosine
        extra[r"\angle " + name] = sp.acos(cosine)
    return values_for(p, extra)


def prism(m):
    given = dict(m.given)
    a, h = given["a"], given["H"]
    p = {
        "A": sp.zeros(3, 1),
        "B": sp.Matrix([a, 0, 0]),
        "C": sp.Matrix([a / 2, sp.sqrt(3) * a / 2, 0]),
    }
    p.update({n + "_1": x + sp.Matrix([0, 0, h]) for n, x in list(p.items())})
    p["D"] = (p["B"] + p["B_1"]) / 2
    p["M"] = (
        (p["B_1"] + p["C_1"]) / 2 if m.names[0] == "upper" else (p["A"] + p["B"]) / 2
    )
    A, B, C, D, A1, B1, C1 = (p[n] for n in ("A", "B", "C", "D", "A_1", "B_1", "C_1"))
    lower = volume(C, A, B, D) + volume(C, A, D, A1)
    upper = volume(A1, D, B1, C1) + volume(A1, D, C1, C)
    return values_for(
        p,
        {
            r"S_{ABDA_1}": area(A, B, D) + area(A, D, A1),
            r"S_{DB_1C_1C}": area(D, B1, C1) + area(D, C1, C),
            r"S_{ABC}": area(A, B, C),
            r"V_{\mathrm{призмы}}": lower + upper,
            "V": upper if m.names[0] == "upper" else lower,
        },
    )


def perpendicular(m):
    given = dict(m.given)
    a = given["a"]
    r = given["q"] / (given["p"] + given["q"])
    u, apex = m.names[:2]
    p = {
        u: sp.Matrix([-a / 2, 0, 0]),
        "B": sp.Matrix([a / 2, 0, 0]),
        "M": sp.Matrix([0, sp.sqrt(3) * a / 2, 0]),
        apex: sp.Matrix([0, 0, sp.sqrt(3) * a / 2]),
        "D": sp.zeros(3, 1),
    }
    p.update(P=(p[u] + p["M"]) / 2, T=p["M"] + r * (p["B"] - p["M"]))
    p["F"] = p["K"] = (p["B"] + p["M"]) / 2
    normal = (p["P"] - p[apex]).cross(p["T"] - p[apex])
    fraction = sp.simplify(normal.dot(p[apex] - p["M"]) / normal.dot(-p["M"]))
    p["E"] = (1 - fraction) * p["M"]
    if r != sp.Rational(1, 2):
        vector = p["T"] - p["P"]
        p["Q"] = p["P"] - p["P"][1] / vector[1] * vector
    base = "ABM" if u == "A" else "BCM"
    return values_for(
        p,
        {
            "S_{" + base + "}": area(*(p[n] for n in base)),
            r"S_{MPT}": area(p["M"], p["P"], p["T"]),
            "V": volume(p["M"], p["P"], p["T"], p[apex]),
        },
    )
