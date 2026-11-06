"""Independent vertices, projections, normals and determinants from givens."""

import re

import sympy as sp
from plane_geometry_oracle import foot


def cosine(u, v):
    return sp.simplify(abs(u.dot(v)) / (u.norm() * v.norm()))


def angle_values(name, p):
    labels = re.findall(r"[A-Z](?:_1)?", name)
    u = p[labels[0]] - p[labels[1]]
    v = p[labels[2]] - p[labels[1]]
    c = cosine(u, v)
    return {
        r"\tan\angle " + name: sp.simplify(u.cross(v).norm() / abs(u.dot(v))),
        r"\cos\angle " + name: c,
    }


def _cube(g):
    a, k = g["a"], g["k"]
    d = a - k
    p = {
        "D": sp.zeros(3, 1),
        "A": sp.Matrix([a, 0, 0]),
        "B": sp.Matrix([a, a, 0]),
        "C": sp.Matrix([0, a, 0]),
    }
    p.update({n + "_1": v + sp.Matrix([0, 0, a]) for n, v in list(p.items())})
    p.update(
        K=sp.Matrix([a, a, k]),
        L=sp.Matrix([k, k, a]),
        M=sp.Matrix([d, d, a]),
        P=sp.Matrix([a, a * (2 * k - a) / k, a]),
    )
    p["N"] = foot(p["B_1"], p["K"], p["C_1"])
    n = (p["P"] - p["K"]).cross(p["C_1"] - p["K"])
    assert sp.simplify(n.dot(p["D_1"] - p["B"])) == 0
    assert sp.simplify((p["L"] - p["K"]).cross(p["D_1"] - p["B"]).norm()) == 0
    assert sp.simplify((p["M"] - p["A_1"]).cross(p["P"] - p["C_1"]).norm()) == 0
    assert (
        sp.simplify(
            (p["A_1"] - p["P"]).norm() / (p["P"] - p["B_1"]).norm() - g["p"] / g["q"]
        )
        == 0
    )
    c = cosine(n, sp.Matrix([0, 1, 0]))
    tan = sp.sqrt(1 - c * c) / c
    small = (
        abs(
            sp.det(
                sp.Matrix.hstack(
                    p["K"] - p["B_1"], p["P"] - p["B_1"], p["C_1"] - p["B_1"]
                )
            )
        )
        / 6
    )
    extra = {
        r"\cos\varphi": c,
        r"\tan\varphi": tan,
        r"V_{\text{куба}}": a**3,
        "V_{B_1KPC_1}": small,
        "S_{KB_1C_1}": (p["K"] - p["B_1"]).cross(p["C_1"] - p["B_1"]).norm() / 2,
        "N_x": d,
        "N_y": k,
        "N_z": a,
        "c": -a * (a + k),
    }
    extra.update(angle_values("PNB_1", p))
    return p, extra, (sp.atan(tan), a**3 - small)


def _box(g):
    a, b, h = g["a"], g["b"], g["height"]
    d = h * g["p"] / (g["p"] + g["q"])
    p = {
        "A": sp.zeros(3, 1),
        "B": sp.Matrix([a, 0, 0]),
        "C": sp.Matrix([a, b, 0]),
        "D": sp.Matrix([0, b, 0]),
    }
    p.update({n + "_1": v + sp.Matrix([0, 0, h]) for n, v in list(p.items())})
    p.update(
        E=sp.Matrix([0, 0, h - d]),
        T=sp.Matrix([a, b / 2, h]),
        F=sp.Matrix([a, 0, h - d / 2]),
        Q=sp.Matrix([a, 0, h - d / 2]),
        U=p["D_1"],
    )
    n = (p["D_1"] - p["E"]).cross(p["T"] - p["E"])
    assert sp.simplify(n.dot(p["F"] - p["E"])) == 0
    if "fp" in g:
        assert (
            sp.simplify(
                (p["B_1"] - p["F"]).norm() / (p["F"] - p["B"]).norm()
                - g["fp"] / g["fq"]
            )
            == 0
        )
        p["K"] = foot(p["B_1"], p["F"], p["T"])
        direction = p["D_1"] - p["E"]
        ft = p["T"] - p["F"]
        parameter = sp.simplify((p["K"] - p["E"]).dot(ft) / direction.dot(ft))
        p["L"] = p["E"] + parameter * direction
        p["X"] = sp.Matrix([a, p["L"][1], p["L"][2]])
        assert sp.simplify((p["L"] - p["K"]).dot(ft)) == 0
        assert sp.simplify(p["X"] - (2 * p["K"] - p["B_1"])) == sp.zeros(3, 1)
        assert sp.simplify((p["L"] - p["X"]).dot(p["X"] - p["K"])) == 0
        extra = angle_values("LKX", p)
        c = cosine(n, sp.Matrix([1, 0, 0]))
        assert sp.simplify(extra[r"\cos\angle LKX"] - c) == 0
        answer = sp.acos(c)
    else:
        p["L"] = sp.Matrix([0, 0, h - d / 2])
        p["H"] = foot(p["A_1"], p["E"], p["Q"])
        extra = angle_values("A_1HD_1", p)
        c = cosine(n, sp.Matrix([0, 1, 0]))
        tan = sp.sqrt(1 - c * c) / c
        assert sp.simplify(extra[r"\tan\angle A_1HD_1"] - tan) == 0
        answer = sp.atan(tan)
    return p, extra, answer


def _pyramid(g):
    a, e = g["a"], g["edge"]
    h = sp.sqrt(e * e - a * a / 2)
    p = {
        "A": sp.Matrix([-a / 2, -a / 2, 0]),
        "B": sp.Matrix([a / 2, -a / 2, 0]),
        "C": sp.Matrix([a / 2, a / 2, 0]),
        "D": sp.Matrix([-a / 2, a / 2, 0]),
        "S": sp.Matrix([0, 0, h]),
        "O": sp.zeros(3, 1),
    }
    p.update(M=(p["S"] + p["A"]) / 2, K=(p["S"] + p["C"]) / 2)
    p["Q"] = (p["M"] + p["K"]) / 2
    assert sp.simplify((p["S"] - p["B"]).dot(p["K"] - p["M"])) == 0
    assert sp.simplify((p["B"] - p["Q"]).dot(p["K"] - p["M"])) == 0
    n = (p["M"] - p["B"]).cross(p["K"] - p["B"])
    c = cosine(n, sp.Matrix([0, 0, 1]))
    extra = angle_values("QBO", p)
    tan = sp.sqrt(1 - c * c) / c
    assert sp.simplify(extra[r"\tan\angle QBO"] - tan) == 0
    return p, extra, sp.atan(tan)


def _prism(g):
    a = g["a"]
    p = {
        "A": sp.zeros(3, 1),
        "B": sp.Matrix([a, 0, 0]),
        "C": sp.Matrix([a / 2, a * sp.sqrt(3) / 2, 0]),
    }
    p.update({n + "_1": v + sp.Matrix([0, 0, a]) for n, v in list(p.items())})
    p["T"] = (p["A_1"] + p["B_1"]) / 2
    assert sp.simplify((p["C_1"] - p["T"]).dot(p["A"] - p["T"])) == 0
    n = (p["T"] - p["A"]).cross(p["C_1"] - p["A"])
    c = cosine(n, sp.Matrix([0, 0, 1]))
    extra = angle_values("A_1TA", p)
    tan = sp.sqrt(1 - c * c) / c
    assert sp.simplify(extra[r"\tan\angle A_1TA"] - tan) == 0
    return p, extra, sp.atan(tan)


def geometry(m):
    g = dict(m.given)
    if m.mode.startswith("cube_parallel"):
        p, extra, answers = _cube(g)
        return p, extra, answers[m.mode.endswith("volume")]
    if m.mode.startswith("box_transverse"):
        return _box(g)
    if m.mode.startswith("square_pyramid_midpoint"):
        return _pyramid(g)
    return _prism(g)
