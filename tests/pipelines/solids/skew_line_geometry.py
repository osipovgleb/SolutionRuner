"""Independent coordinates verify edge claims and the smaller line angle."""

import sympy as sp
from plane_geometry_oracle import foot


def cosine(u, v):
    return sp.simplify(abs(u.dot(v)) / (u.norm() * v.norm()))


def prism(m):
    a, b, h, fraction = (dict(m.given)[k] for k in ("a", "b", "height", "fraction"))
    p = {
        "A": sp.zeros(3, 1),
        "C": sp.Matrix([b, 0, 0]),
        "B": sp.Matrix([b / 2, sp.sqrt(a * a - b * b / 4), 0]),
    }
    p.update({n + "_1": x + sp.Matrix([0, 0, h]) for n, x in list(p.items())})
    p["K"] = (p["A_1"] + p["B_1"]) / 2
    p["M"] = p["A"] + fraction * (p["C"] - p["A"])
    if m.names[0] == "quarter":
        p["N"], p["L"] = (p["A"] + p["B"]) / 2, (p["A"] + p["C"]) / 2
        assert sp.simplify((p["M"] - p["K"]).dot(p["C"] - p["A"])) == 0
    else:
        p["N"] = (p["A"] + p["B"]) / 2
        assert sp.simplify((p["M"] - p["K"]).norm() - (p["B"] - p["K"]).norm()) == 0
    p["H"], p["E"] = (foot(p[n], p["A"], p["B"]) for n in ("M", "C"))
    normal = (p["B"] - p["A"]).cross(p["B_1"] - p["A"])
    return p, sp.asin(cosine(p["M"] - p["K"], normal))


def tetrahedron(m):
    a, b = (dict(m.given)[k] for k in ("p", "q"))
    p = {"D": sp.Matrix([0, 0, 1])}
    first = m.names[0] == "DC"
    p.update(
        A=sp.zeros(3, 1) if first else sp.Matrix([a, 0, 1]),
        B=sp.Matrix([0, b, 0]) if first else sp.zeros(3, 1),
        C=sp.Matrix([a, 0, 1]) if first else sp.Matrix([0, b, 0]),
    )
    p["E"], p["F"] = (p["D"] + p["B"]) / 2, (p["A"] + p["C"]) / 2
    p["K"] = (p["B"] + p["C" if first else "A"]) / 2
    p["M"] = (p["D"] + p["A" if first else "C"]) / 2
    p["O"] = (p["E"] + p["F"]) / 2
    assert sp.simplify((p["E"] + p["F"] - p["K"] - p["M"]).norm()) == 0
    assert sp.simplify((p["E"] - p["K"]).dot(p["M"] - p["E"])) == 0
    return p, sp.acos(cosine(p["F"] - p["E"], p["K"] - p["M"]))


def cube(m):
    a = dict(m.given).get("a", sp.S.One)
    p = {
        "A": sp.zeros(3, 1),
        "B": sp.Matrix([a, 0, 0]),
        "C": sp.Matrix([a, a, 0]),
        "D": sp.Matrix([0, a, 0]),
    }
    p.update({n + "_1": x + sp.Matrix([0, 0, a]) for n, x in list(p.items())})
    kind, origin, vertical, far, method = m.names
    p["E"] = (p[vertical] + p[vertical + "_1"]) / 2
    p["F"] = p[vertical + "_1"] + (p[vertical + "_1"] - p[vertical]) / 2
    if method == "coordinates":
        assert sp.simplify((p["D"] - p["B_1"]).dot(p["C"] - p["A"])) == 0
    u = p["E"] - p[origin]
    v = p[far] - p[origin + "_1"] if kind == "space" else p["D"] - p["A"]
    if kind == "space":
        assert sp.simplify((p["F"] - p[origin + "_1"]).cross(u).norm()) == 0
        return p, sp.acos(cosine(u, v))
    return p, sp.atan(sp.simplify(u.cross(v).norm() / abs(u.dot(v))))


def pyramid(m):
    e, c = (dict(m.given)[k] for k in ("e", "c"))
    a = sp.sqrt(2 * e * e * (1 - c))
    radius = a / sp.sqrt(3)
    p = {
        "S": sp.Matrix([0, 0, sp.sqrt(e * e - radius * radius)]),
        "A": sp.Matrix([radius, 0, 0]),
        "B": sp.Matrix([-radius / 2, a / 2, 0]),
        "C": sp.Matrix([-radius / 2, -a / 2, 0]),
        "H": sp.zeros(3, 1),
    }
    p["M"], p["N"] = (p["S"] + p["C"]) / 2, (p["A"] + p["C"]) / 2
    assert sp.simplify((p["M"] - p["N"]).cross(p["S"] - p["A"]).norm()) == 0
    for apex, x, y in (("A", "B", "C"), ("B", "A", "C")):
        assert sp.simplify((p["S"] - p[apex]).dot(p[x] - p[y])) == 0
    return p, cosine(p["B"] - p["M"], p["S"] - p["A"])


def geometry(m):
    return {
        "triangle_prism_split_edge_projection_angle": prism,
        "tetra_parallel_midpoint_diagonal_angle": tetrahedron,
        "cube_midpoint_skew_angle": cube,
        "triangle_pyramid_midpoint_skew_cosine": pyramid,
    }[m.mode](m)
