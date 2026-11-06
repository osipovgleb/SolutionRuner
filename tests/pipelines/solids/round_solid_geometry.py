"""Independent axial sections, tangent planes and determinants validate final solid proofs."""

import sympy as sp
from projection_plane_equation_oracle import values_for


def area(a, b, c):
    return sp.simplify((b - a).cross(c - a).norm() / 2)


def volume(a, b, c, d):
    return sp.simplify(abs(sp.det(sp.Matrix.hstack(b - a, c - a, d - a))) / 6)


def concentric(m):
    g = dict(m.given)
    first, second = g["alpha_area"], g["beta_area"]
    distance = sp.Integer(2)
    inner = sp.sqrt(distance**2 + first / sp.pi)
    p = {
        "O": sp.zeros(3, 1),
        "F": sp.Matrix([0, distance, 0]),
        "A": sp.Matrix([0, inner, 0]),
        "D": sp.Matrix([sp.sqrt(first / sp.pi), distance, 0]),
        "C": sp.Matrix([-sp.sqrt((first + second) / sp.pi), distance, 0]),
        "B": sp.Matrix([sp.sqrt(second / sp.pi), inner, 0]),
        "X": sp.Matrix([sp.sqrt(first / sp.pi) / 2, distance, 0]),
    }
    return (
        p,
        values_for(
            p,
            {
                "R": inner,
                r"S_{\alpha}": first,
                r"S_{\beta}": second,
                "S": sp.pi * (p["C"] - p["F"]).norm() ** 2,
            },
        ),
        first + second,
    )


def axis_chord(m):
    g = dict(m.given)
    a, b, h = g["a"], g["b"], g["H"]
    diameter = sp.sqrt(a * a + b * b)
    radius = diameter / 2
    p = {
        "A": sp.Matrix([radius, 0, 0]),
        "C": sp.Matrix([-radius, 0, 0]),
        "B": sp.Matrix([(b * b - a * a) / (2 * diameter), a * b / diameter, 0]),
    }
    p.update({n + "_1": p[n] + sp.Matrix([0, 0, h]) for n in ("B", "C")})
    d = p["C_1"] - p["A"]
    p["K"] = p["A"] + (p["B"] - p["A"]).dot(d) / d.dot(d) * d
    u, v = p["A"] - p["C_1"], p["C"] - p["C_1"]
    angle = sp.acos(sp.simplify(u.dot(v) / (u.norm() * v.norm())))
    sin_alpha, cos_alpha = p["B"][0] / radius, p["B"][1] / radius
    extra = {
        "r": radius,
        "h": h,
        "L": 2 * sp.pi * radius,
        r"S_{\mathrm{бок}}": 2 * sp.pi * radius * h,
        r"\sin\alpha": sin_alpha,
        r"\cos\alpha": cos_alpha,
        r"\sin^2\alpha": sin_alpha**2,
        r"\cos^2\alpha": cos_alpha**2,
        r"\tan\angle AC_1C": u.cross(v).norm() / u.dot(v),
        r"\angle AC_1C": angle,
    }
    answer = (
        angle
        if m.names[0] == "angle"
        else (p["B"] - p["K"]).norm()
        if m.names[0] == "distance"
        else extra[r"S_{\mathrm{бок}}"]
    )
    return p, values_for(p, extra), answer


def insphere(m):
    g = dict(m.given)
    e, h = g["e"], g["H"]
    a = sp.sqrt(e * e - h * h)
    p = {
        n: sp.Matrix([a * sp.cos(i * sp.pi / 3), a * sp.sin(i * sp.pi / 3), 0])
        for i, n in enumerate("ABCDEF")
    }
    p.update(H=sp.zeros(3, 1), M=sp.Matrix([0, 0, h]), N=(p["A"] + p["B"]) / 2)
    base = sum(area(p["H"], p[x], p[y]) for x, y in zip("ABCDEF", "BCDEFA"))
    lateral = sum(area(p["M"], p[x], p[y]) for x, y in zip("ABCDEF", "BCDEFA"))
    V = sum(volume(p["M"], p["H"], p[x], p[y]) for x, y in zip("ABCDEF", "BCDEFA"))
    radius = sp.simplify(3 * V / (base + lateral))
    p["O"] = sp.Matrix([0, 0, radius])
    direction = p["N"] - p["M"]
    p["K"] = (
        p["M"] + (p["O"] - p["M"]).dot(direction) / direction.dot(direction) * direction
    )
    assert sp.simplify((p["K"] - p["O"]).norm() - radius) == 0
    u, v = p["M"] - p["N"], p["H"] - p["N"]
    cosine = sp.simplify(u.dot(v) / (u.norm() * v.norm()))
    extra = {
        "r": radius,
        "V": V,
        "S": 4 * sp.pi * radius**2,
        r"S_{\mathrm{осн}}": base,
        r"S_{\mathrm{бок}}": lateral,
        r"S_{\mathrm{полн}}": base + lateral,
        r"\cos\angle MNH": cosine,
        r"\sin\angle MNH": u.cross(v).norm() / (u.norm() * v.norm()),
        r"\angle MNH": sp.acos(cosine),
    }
    return p, values_for(p, extra), extra["S"]


def rectangle(m):
    g = dict(m.given)
    R, h = g["R"], g["H"]
    offset = sp.sqrt(3) * R / 2
    p = {
        "O": sp.zeros(3, 1),
        "C": sp.Matrix([R, 0, 0]),
        "D": sp.Matrix([-R, 0, 0]),
        "H": sp.Matrix([-offset, 0, 0]),
        "M": sp.Matrix([-offset, -R / 2, 0]),
        "N": sp.Matrix([-offset, R / 2, 0]),
    }
    p.update(A=p["M"] + sp.Matrix([0, 0, h]), B=p["N"] + sp.Matrix([0, 0, h]))
    V = volume(p["C"], p["A"], p["B"], p["N"]) + volume(p["C"], p["A"], p["N"], p["M"])
    surface = (p["B"] - p["A"]).cross(p["M"] - p["A"]).norm()
    return p, values_for(p, {"R": R, "V": V, r"S_{ABNM}": surface}), V
