"""Independent coordinates, determinants and normals for the four proof families."""

import sympy as sp
from plane_geometry_oracle import foot


def cosine(points, first, second):
    def normal(names):
        a, b, c = (points[n] for n in names)
        return (b - a).cross(c - a)

    u, v = normal(first), normal(second)
    return sp.simplify(abs(u.dot(v)) / (u.norm() * v.norm()))


def tetra(m):
    g = dict(m.given)
    a, t = g["a"], g["t"]
    p = {
        "A": sp.zeros(3, 1),
        "B": sp.Matrix([a, 0, 0]),
        "D": sp.Matrix([a / 2, a * sp.sqrt(3) / 2, 0]),
        "C": sp.Matrix([a / 2, a * sp.sqrt(3) / 6, a * sp.sqrt(sp.Rational(2, 3))]),
    }
    p.update(M=p["B"] * t / a, K=p["D"] * t / a)
    p.update(A_1=(p["M"] + p["K"]) / 2, A_2=(p["B"] + p["D"]) / 2)
    p["O"] = (p["A"] + p["B"] + p["D"]) / 3

    def volume(names):
        x, y, z, w = (p[n] for n in names)
        return abs(sp.det(sp.Matrix.hstack(y - x, z - x, w - x))) / 6

    total, corner = volume(("A", "B", "C", "D")), volume(("A", "M", "C", "K"))
    assert sp.simplify((total - corner) / corner - (a * a - t * t) / (t * t)) == 0
    extra = {
        "h": p["C"][2],
        r"V_{ABCD}": total,
        r"V_{CMKA}": corner,
        r"V_{CMKDB}": total - corner,
        r"S_{ABD}": (p["B"] - p["A"]).cross(p["D"] - p["A"]).norm() / 2,
        r"S_{AMK}": (p["M"] - p["A"]).cross(p["K"] - p["A"]).norm() / 2,
    }
    return p, extra, cosine(p, ("C", "B", "D"), ("C", "M", "K"))


def box(m):
    cube = m.mode == "cube_projection_plane_angle"
    a, b, h = (
        (sp.Rational(7, 3),) * 3
        if cube
        else tuple(dict(m.given)[k] for k in ("a", "b", "height"))
    )
    p = {
        "A": sp.zeros(3, 1),
        "B": sp.Matrix([a, 0, 0]),
        "C": sp.Matrix([a, b, 0]),
        "D": sp.Matrix([0, b, 0]),
    }
    p.update({n + "_1": v + sp.Matrix([0, 0, h]) for n, v in list(p.items())})
    if cube:
        if m.names[0] == "center":
            p.update(M=(p["A_1"] + p["B"]) / 2, O=(p["A"] + p["C_1"]) / 2)
            pair = (("B", "A_1", "C_1"), ("B", "A_1", "D_1"))
        else:
            p["M"] = (p["A"] + p["D_1"]) / 2
            pair = (("A", "B_1", "D_1"), ("A", "C", "D_1"))
        c = cosine(p, *pair)
        return p, {"a": a}, c if m.names[2] == "cosine" else sp.acos(c)
    purpose = m.names[0]
    if purpose == "side":
        p["E"] = foot(p["A"], p["B"], p["A_1"])
        pair = (("C", "D", "D_1"), ("B", "D", "A_1"))
    elif purpose == "top":
        p["E"] = foot(p["D"], p["A"], p["C"])
        pair = (("A", "C", "D_1"), ("A_1", "B_1", "C_1"))
    else:
        p["H"] = foot(p["A"], p["B"], p["D"])
        pair = (("A", "B", "C"), ("A_1", "D", "B"))
    c = cosine(p, *pair)
    tangent = sp.simplify(sp.sqrt(1 - c * c) / c)
    return p, {}, tangent if m.names[1] == "tangent" else sp.atan(tangent)


def rhombus(m):
    g = dict(m.given)
    a, h, theta = (g[k] for k in ("a", "height", "theta"))
    s, c = sp.sin(theta * sp.pi / 180), sp.cos(theta * sp.pi / 180)
    p = {
        "A": sp.zeros(3, 1),
        "B": sp.Matrix([a, 0, 0]),
        "D": sp.Matrix([a * c, a * s, 0]),
    }
    p["C"] = p["B"] + p["D"]
    p.update({n + "_1": v + sp.Matrix([0, 0, h]) for n, v in list(p.items())})
    p["H"] = foot(p["D"], p["A"], p["B"])
    lateral = 4 * (p["B"] - p["A"]).cross(p["A_1"] - p["A"]).norm()
    base = (p["B"] - p["A"]).cross(p["D"] - p["A"]).norm()
    extra = {
        "a": a,
        "H": h,
        r"\sin\alpha": s,
        r"\sin " + sp.latex(theta) + r"^\circ": s,
        r"S_{\mathrm{бп}}": lateral,
        r"S_{\mathrm{осн}}": base,
        r"S_{\mathrm{пп}}": lateral + 2 * base,
    }
    c = cosine(p, ("A", "C_1", "B"), ("A", "B", "D"))
    return p, extra, sp.atan(sp.simplify(sp.sqrt(1 - c * c) / c))


def geometry(m):
    if m.mode == "tetra_equal_edge_cut_cosine":
        return tetra(m)
    if m.mode == "rhombus_prism_section_angle":
        return rhombus(m)
    return box(m)
