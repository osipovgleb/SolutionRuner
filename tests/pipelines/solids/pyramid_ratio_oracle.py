"""Verify scale, section and cut coefficients with independent geometric witnesses."""

import sympy as sp
from pyramid_regular_oracle import area, norm, volume


def tetra(points):
    p, a, b, c = points
    return sp.simplify(sp.Abs(sp.det(sp.Matrix.hstack(a - p, b - p, c - p))) / 6)


def scale(m):
    k = m.given[0]
    if m.body == "правильного тетраэдра":
        points = [
            sp.Matrix(p) for p in [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
        ]
        v = tetra(points)
        a = norm(points[1] - points[0])
        a0 = area(points[:3])
        s = 4 * a0
    else:
        a = sp.Integer(2)
        a0 = sp.sqrt(3) if m.body == "октаэдра" else sp.Integer(2)
        s = 8 * a0 if m.body == "октаэдра" else 4 + 4 * a0
        v = sp.Rational(4, 3)
    values = {
        "k": k,
        "a_0": a,
        "a_1": a * k,
        "A_0": a0,
        "A_1": a0 * k * k,
        "S_0": s,
        "S_1": s * k * k,
        "h_0": 2 * a0 / a,
        "h_1": 2 * a0 * k / a,
        "B_0": sp.Integer(4),
        "B_1": sp.Integer(4),
        "H_0": sp.Integer(1),
        "H_1": k,
        "V_0": v,
    }
    if m.kind == "scale_volume":
        new = tetra([p * k for p in points])
        values["V_1"] = new
        expected = new / v
    elif m.kind == "scale_height":
        base = [sp.Matrix(p) for p in [(0, 0, 0), (2, 0, 0), (2, 2, 0), (0, 2, 0)]]
        old = volume(sp.Matrix((1, 1, 1)), base)
        new = volume(sp.Matrix((1, 1, k)), base)
        values.update(V_0=old, V_1=new)
        expected = new / old
    else:
        triangle = [sp.Matrix(p) for p in [(0, 0, 0), (2, 0, 0), (0, 2, 0)]]
        expected = area([p * k for p in triangle]) / area(triangle)
    return values, sp.simplify(expected)


def section(m):
    a = m.given[0]
    if m.kind == "tetra_section":
        t = [
            sp.Matrix(p) * a / (2 * sp.sqrt(2))
            for p in [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
        ]
        p = [(t[0] + t[2]) / 2, (t[0] + t[3]) / 2, (t[1] + t[3]) / 2, (t[1] + t[2]) / 2]
    else:
        base = [sp.Matrix(p) for p in [(0, 0, 0), (a, 0, 0), (a, a, 0), (0, a, 0)]]
        apex = sp.Matrix((a / 2, a / 2, a / sp.sqrt(2)))
        p = [(b + apex) / 2 for b in base]
    side = norm(p[1] - p[0])
    assert (p[1] - p[0]).dot(p[2] - p[1]) == 0
    return {"a": a, "t": side, "k": sp.Rational(1, 2), "S": area(p)}, area(p)


def _hex(m):
    base = [
        sp.Matrix((sp.cos(i * sp.pi / 3), sp.sin(i * sp.pi / 3), 0)) for i in range(6)
    ]
    part = area(base[:3])
    height = 3 * m.given[0] / part
    apex = sp.Matrix((0, 0, height))
    full = volume(apex, base)
    small = volume(apex, base[:3])
    return {"a": sp.S.One, "B": area(base), "B_p": part, "V": full, "V_p": small}, full


def _quarter(m):
    v = m.given[0]
    if m.kind == "square_midpoint":
        base = [sp.Matrix(p) for p in [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]]
        height = 3 * v
        apex = sp.Matrix((sp.Rational(1, 2), sp.Rational(1, 2), height))
        e = (apex + base[1]) / 2
        part = tetra([e, *base[:3]])
        b0 = 1
        b1 = sp.Rational(1, 2)
        h1 = height / 2
    else:
        base = [sp.Matrix(p) for p in [(0, 0, 0), (2, 0, 0), (0, 2, 0)]]
        height = 3 * v / 2
        apex = sp.Matrix((0, 0, height))
        m1 = (base[0] + base[2]) / 2
        m2 = (base[1] + base[2]) / 2
        part = tetra([apex, base[2], m1, m2])
        b0 = 2
        b1 = sp.Rational(1, 2)
        h1 = height
    return {
        "k": sp.Rational(1, 2),
        "B_0": sp.sympify(b0),
        "B_1": b1,
        "H_0": height,
        "H_1": h1,
        "V_0": v,
        "V_1": part,
    }, part


def _edge(m):
    v, r1, r2 = m.given
    h = 6 * v
    s = sp.Matrix((0, 0, h))
    a = sp.Matrix((0, 0, 0))
    b = sp.Matrix((1, 0, 0))
    c = sp.Matrix((0, 1, 0))
    e = (s * r2 + c * r1) / (r1 + r2)
    v1 = tetra([s, a, b, e])
    v2 = tetra([c, a, b, e])
    larger = sp.Max(v1, v2)
    assert sp.simplify(v1 + v2 - v) == 0
    return {
        "r_1": r1,
        "r_2": r2,
        "V_0": v,
        "V_1": v1,
        "V_2": v2,
        "V": larger,
        "k": larger / v,
    }, larger


def _sixth(m):
    v = m.given[0]
    if m.kind == "box_tetrahedron":
        u = sp.Matrix((2, 0, 0))
        w = sp.Matrix((1, 3, 0))
        z = sp.Matrix((1, 1, 4)) * v / 24
        base = [sp.zeros(3, 1), u, u + w, w]
        apex = u + z
        b = area(base)
        h = z[2]
        part = tetra([apex, *base[:3]])
        return {
            "B": b,
            "H": h,
            "B_p": area(base[:3]),
            "H_p": h,
            "V_0": v,
            "V": part,
        }, part
    a = sp.real_root(v, 3)
    base = [sp.Matrix(p) for p in [(0, 0, 0), (a, 0, 0), (a, a, 0), (0, a, 0)]]
    apex = sp.Matrix((a / 2, a / 2, a / 2))
    part = volume(apex, base)
    return {"a": a, "B": area(base), "H": a / 2, "V_0": v, "V": part}, part


def quantities(m):
    if m.kind.startswith("scale_"):
        return scale(m)
    if m.kind.endswith("_section"):
        return section(m)
    if m.kind == "hex_whole":
        return _hex(m)
    if m.kind in {"square_midpoint", "midline_cut"}:
        return _quarter(m)
    if m.kind == "edge_cut":
        return _edge(m)
    return _sixth(m)
