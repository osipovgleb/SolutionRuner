"""Independent common perpendiculars, opposite vertices and pyramid sections."""

import sympy as sp
from plane_angle_geometry import cosine
from plane_geometry_oracle import foot


def _trig(points, name, kind):
    import re

    a, b, c = re.findall(r"[A-Z](?:_1)?", name)
    u, v = points[a] - points[b], points[c] - points[b]
    return sp.simplify(
        u.dot(v) / (u.norm() * v.norm())
        if kind == "cos"
        else u.cross(v).norm() / abs(u.dot(v))
    )


def _box(g):
    a, b, h = g["a"], g["b"], g["height"]
    p = {
        "A": sp.zeros(3, 1),
        "B": sp.Matrix([a, 0, 0]),
        "C": sp.Matrix([a, b, 0]),
        "D": sp.Matrix([0, b, 0]),
    }
    p.update({k + "_1": v + sp.Matrix([0, 0, h]) for k, v in list(p.items())})
    p.update(O=p["C"] / 2, O_1=(p["B_1"] + p["D_1"]) / 2)
    for first, second, third, fourth in [
        ("A", "C", "B_1", "D_1"),
        ("A_1", "D_1", "B", "D"),
    ]:
        u = p[second] - p[first]
        v = p[fourth] - p[third]
        n = u.cross(v)
        assert sp.simplify(abs((p[third] - p[first]).dot(n)) / n.norm() - h) == 0
    t = _trig(p, "BD_1D", "tan")
    assert (
        sp.simplify(
            cosine(p["D_1"] - p["B"], p["D_1"] - p["D"]) - 1 / sp.sqrt(1 + t * t)
        )
        == 0
    )
    return p, {r"\tan\angle BD_1D": t}, sp.atan(t)


def _square(g, names):
    a, h, p0, q0 = g["a"], g["height"], g["p"], g["q"]
    e = h * p0 / (p0 + q0)
    p = {
        "A": sp.zeros(3, 1),
        "B": sp.Matrix([a, 0, 0]),
        "C": sp.Matrix([a, a, 0]),
        "D": sp.Matrix([0, a, 0]),
    }
    p.update({k + "_1": v + sp.Matrix([0, 0, h]) for k, v in list(p.items())})
    p.update(
        E=sp.Matrix([0, 0, e]),
        K=sp.Matrix([0, -a * e / (h - e), 0]),
        O=(p["B"] + p["D_1"]) / 2,
    )
    n = (p["E"] - p["B"]).cross(p["D_1"] - p["B"])
    first, second = names
    for name, point in [("P", p[first]), ("L", p[second])]:
        p[name] = sp.simplify(point - n * n.dot(point - p["B"]) / n.dot(n))
    assert sp.simplify((p[first] - p["P"]).norm() - (p[second] - p["L"]).norm()) == 0
    assert sp.simplify((p[first] + p[second]) / 2 - p["O"]) == sp.zeros(3, 1)
    assert sp.simplify((p["K"] - p["E"]).cross(p["D_1"] - p["E"]).norm()) == 0
    p["H"] = foot(p["A"], p["K"], p["B"])
    t = _trig(p, "AHE", "tan")
    c = cosine(n, sp.Matrix([0, 0, 1]))
    assert sp.simplify(c - 1 / sp.sqrt(1 + t * t)) == 0
    return (
        p,
        {
            r"\tan\angle AHE": t,
            r"\tan\varphi": t,
            r"\cos\varphi": c,
            "N_x": h - e,
            "N_y": e,
            "N_z": -a,
        },
        sp.atan(t),
    )


def _pyramid(g):
    a, h = g["a"], g["height"]
    p = {
        "A": sp.Matrix([0, a * sp.sqrt(3) / 2, 0]),
        "B": sp.Matrix([-a / 2, 0, 0]),
        "C": sp.Matrix([a / 2, 0, 0]),
    }
    p["H"] = (p["A"] + p["B"] + p["C"]) / 3
    p["S"] = p["H"] + sp.Matrix([0, 0, h])
    p["N"] = (p["B"] + p["C"]) / 2
    p.update(K=(p["S"] + p["A"]) / 2, Q=(p["S"] + p["B"]) / 2, P=(p["S"] + p["C"]) / 2)
    p["R"] = (p["S"] + p["N"]) / 2
    p["T"] = sp.Matrix([0, p["R"][1], 0])
    assert sp.simplify((p["P"] - p["R"]).cross(p["Q"] - p["R"]).norm()) == 0
    assert sp.simplify((p["P"] - p["A"]).norm() - (p["Q"] - p["A"]).norm()) == 0
    assert sp.simplify((p["A"] - p["R"]).dot(p["P"] - p["Q"])) == 0
    n = (p["P"] - p["A"]).cross(p["Q"] - p["A"])
    c = cosine(n, sp.Matrix([0, 0, 1]))
    extra = {
        r"\cos\angle HNS": _trig(p, "HNS", "cos"),
        r"\cos\angle RAN": _trig(p, "RAN", "cos"),
        r"\tan\angle RAN": _trig(p, "RAN", "tan"),
    }
    assert sp.simplify(extra[r"\cos\angle RAN"] - c) == 0
    return p, extra, sp.acos(c)


def _ratio(g, names):
    a, e, r = g["a"], g["e"], g["p"] / (g["p"] + g["q"])
    p = {
        "A": sp.Matrix([0, a * sp.sqrt(3) / 2, 0]),
        "B": sp.Matrix([-a / 2, 0, 0]),
        "C": sp.Matrix([a / 2, 0, 0]),
    }
    center = (p["A"] + p["B"] + p["C"]) / 3
    p["S"] = center + sp.Matrix([0, 0, sp.sqrt(e * e - a * a / 3)])
    p["T"] = (p["B"] + p["C"]) / 2
    ab, sc, ac, sb = (
        ("L", "N", "K", "M") if names == ("L", "N") else ("K", "M", "L", "N")
    )
    p[ab] = p["A"] + r * (p["B"] - p["A"])
    p[ac] = p["A"] + r * (p["C"] - p["A"])
    p[sc] = p["S"] + r * (p["C"] - p["S"])
    p[sb] = p["S"] + r * (p["B"] - p["S"])
    p["P"] = p["A"] + r * (p["T"] - p["A"])
    p["Q"] = p["S"] + r * (p["T"] - p["S"])
    normal = (p[ac] - p[ab]).cross(p[sc] - p[ab])
    assert sp.simplify(normal.dot(p["S"] - p["A"])) == 0
    assert sp.simplify(normal.dot(p["A"] - p[ab])) != 0
    assert sp.simplify((p[sc] - p[ac]).cross(p["S"] - p["A"]).norm()) == 0
    signed = _trig(p, "AST", "cos")
    c = cosine(normal, (p["B"] - p["S"]).cross(p["C"] - p["S"]))
    assert sp.simplify(abs(signed) - c) == 0
    return p, {r"\cos\angle AST": signed, r"\cos\varphi": c}, sp.acos(c)


def geometry(m):
    g = dict(m.given)
    if m.mode == "box_skew_distance_normal_angle":
        return _box(g)
    if m.mode == "square_prism_opposite_vertex_plane_angle":
        return _square(g, m.names)
    if m.mode == "triangle_pyramid_midpoint_plane_angle":
        return _pyramid(g)
    return _ratio(g, m.names)
