"""Coordinates independently verify median claims and line-to-plane quantities."""

import sympy as sp
from plane_geometry_oracle import foot


def normal(p, names):
    a, b, c = (p[n] for n in names)
    return (b - a).cross(c - a)


def sine(v, n):
    return sp.simplify(abs(v.dot(n)) / (v.norm() * n.norm()))


def box(m):
    g = dict(m.given)
    a = g.get("AB", g.get("C_1D_1"))
    b = g.get("BC", g.get("AD", g.get("A_1D_1")))
    h = g.get("AA_1", g.get("CC_1"))
    p = {
        "A": sp.zeros(3, 1),
        "B": sp.Matrix([a, 0, 0]),
        "C": sp.Matrix([a, b, 0]),
        "D": sp.Matrix([0, b, 0]),
    }
    p.update({n + "_1": v + sp.Matrix([0, 0, h]) for n, v in list(p.items())})
    side = m.names[0] == "midpoint_side"
    p["E"] = (p["A"] + p["B" if side else "A_1"]) / 2
    p["F"] = (p["B_1"] + p["C_1"]) / 2 if side else (p["C_1"] + p["D_1"]) / 2
    value = sine(
        p["F"] - p["E"], normal(p, ("A", "D", "D_1") if side else ("A", "B", "C"))
    )
    tangent = sp.simplify(value / sp.sqrt(1 - value * value))
    return p, tangent if m.names[2] == "tangent" else sp.atan(tangent)


def median(m):
    a, e = (dict(m.given)[k] for k in ("a", "e"))
    h = sp.sqrt(e * e - a * a / 3)
    p = {
        "B": sp.Matrix([-a / 2, 0, 0]),
        "C": sp.Matrix([a / 2, 0, 0]),
        "A": sp.Matrix([0, a * sp.sqrt(3) / 2, 0]),
        "O": sp.Matrix([0, a * sp.sqrt(3) / 6, 0]),
        "N": sp.zeros(3, 1),
    }
    p["S"] = p["O"] + sp.Matrix([0, 0, h])
    p["M"] = (p["A"] + p["S"]) / 2
    p["M_1"] = sp.Matrix([p["M"][0], p["M"][1], 0])
    lengths = [
        (p["A"] - p["M_1"]).norm(),
        (p["M_1"] - p["O"]).norm(),
        (p["O"] - p["N"]).norm(),
    ]
    assert all(sp.simplify(x - lengths[0]) == 0 for x in lengths)
    assert (p["S"] - p["A"]).dot(p["C"] - p["B"]) == 0
    s = sine(p["M"] - p["N"], sp.Matrix([0, 0, 1]))
    return p, sp.atan(sp.simplify(s / sp.sqrt(1 - s * s)))


def prism(m):
    g = dict(m.given)
    h = g["height"]
    if m.symbols["base"] == "isosceles":
        a, b = g["a"], g["b"]
        p = {
            "B": sp.Matrix([-b / 2, 0, 0]),
            "C": sp.Matrix([b / 2, 0, 0]),
            "A": sp.Matrix([0, sp.sqrt(a * a - b * b / 4), 0]),
        }
    else:
        hyp, leg = g["hyp"], g["leg"]
        p = {
            "A": sp.zeros(3, 1),
            "B": sp.Matrix([hyp, 0, 0]),
            "C": sp.Matrix(
                [
                    (hyp * hyp - leg * leg) / hyp,
                    sp.sqrt(hyp * hyp - leg * leg) * leg / hyp,
                    0,
                ]
            ),
        }
    p.update({n + "_1": v + sp.Matrix([0, 0, h]) for n, v in list(p.items())})
    if m.symbols["base"] == "isosceles":
        p["M"] = (p["B_1"] + p["C_1"]) / 2
        p["L"] = (p["B"] + p["C"]) / 2
        if m.symbols["claim"] == "square":
            assert sp.simplify((p["A_1"] - p["M"]).norm() - h) == 0
        else:
            assert normal(p, ("B", "A_1", "M")).dot(normal(p, ("B", "C", "C_1"))) == 0
        s = sine(p["A_1"] - p["B"], normal(p, ("B", "C", "C_1")))
    else:
        p["H"] = foot(p["C_1"], p["A_1"], p["B_1"])
        s = sine(p["C_1"] - p["B"], normal(p, ("A", "B", "B_1")))
    return p, sp.asin(s)


def tetrahedron(m):
    g = dict(m.given)
    if m.mode == "symmetric_tetrahedron_line_plane_angle":
        u, v, w = (g[k] for k in ("u", "v", "w"))
        sn, an = sp.sqrt(u * u - w * w / 4), sp.sqrt(v * v - w * w / 4)
        y = (sn * sn + an * an - w * w) / (2 * sn)
        p = {
            "N": sp.zeros(3, 1),
            "B": sp.Matrix([-w / 2, 0, 0]),
            "C": sp.Matrix([w / 2, 0, 0]),
            "S": sp.Matrix([0, sn, 0]),
            "A": sp.Matrix([0, y, sp.sqrt(an * an - y * y)]),
        }
        p["M"] = foot(p["A"], p["S"], p["N"])
        assert sp.simplify((p["A"] - p["S"]).dot(p["C"] - p["B"])) == 0
        s = sine(p["A"] - p["S"], normal(p, ("S", "B", "C")))
        return p, sp.acos(sp.sqrt(1 - s * s))
    a, e, ratio = (g[k] for k in ("a", "e", "ratio"))
    p = {
        "A": sp.Matrix([a / sp.sqrt(3), 0, 0]),
        "B": sp.Matrix([-a / (2 * sp.sqrt(3)), a / 2, 0]),
        "C": sp.Matrix([-a / (2 * sp.sqrt(3)), -a / 2, 0]),
        "S": sp.Matrix([0, 0, sp.sqrt(e * e - a * a / 3)]),
    }
    fraction = ratio / (1 + ratio)
    p["P"] = p["A"] + fraction * (p["B"] - p["A"])
    p["K"] = p["C"] + fraction * (p["B"] - p["C"])
    p["M"] = p["A"] + fraction * (p["S"] - p["A"])
    p["L"] = p["C"] + fraction * (p["S"] - p["C"])
    p["H"] = (p["A"] + p["C"]) / 2
    p["T"] = foot(p["H"], p["B"], p["S"])
    p["R"] = p["B"] + (p["H"] - p["B"]) / (1 + ratio)
    p["Q"] = p["S"] + (p["H"] - p["S"]) / (1 + ratio)
    n = (p["K"] - p["P"]).cross(p["S"] - p["B"])
    assert sp.simplify(n.dot(p["M"] - p["P"])) == 0
    assert sp.simplify(n.dot(p["L"] - p["P"])) == 0
    assert sp.simplify((p["K"] - p["P"]).dot(p["M"] - p["P"])) == 0
    return p, sp.simplify(abs(n.dot(p["S"] - p["P"])) / n.norm())


def geometry(m):
    if m.mode == "box_tetrahedron_line_projection_angle":
        return box(m)
    if m.mode == "triangle_pyramid_midpoint_projection_angle":
        return median(m)
    if m.mode == "triangle_prism_line_projection_angle":
        return prism(m)
    return tetrahedron(m)
