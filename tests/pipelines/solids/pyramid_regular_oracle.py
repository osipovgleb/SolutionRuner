"""Check pyramid dimensions with independent coordinates, face areas and determinants."""

import sympy as sp
from sympy.geometry import Point2D, Polygon


def norm(v):
    return sp.sqrt(sp.simplify(v.dot(v)))


def area(points):
    origin = points[0]
    return sp.simplify(
        sum(
            norm((points[i] - origin).cross(points[i + 1] - origin)) / 2
            for i in range(1, len(points) - 1)
        )
    )


def volume(apex, base):
    origin = base[0]
    return sp.simplify(
        sum(
            sp.Abs(
                sp.det(
                    sp.Matrix.hstack(
                        base[i] - origin, base[i + 1] - origin, apex - origin
                    )
                )
            )
            / 6
            for i in range(1, len(base) - 1)
        )
    )


def regular(m):
    q = m.q
    a = q["a"]
    h = q["H"]
    root = sp.sqrt(3)
    coordinates = {
        "triangle": [(0, 0), (1, 0), (sp.Rational(1, 2), root / 2)],
        "square": [(0, 0), (1, 0), (1, 1), (0, 1)],
        "hexagon": [
            (1, 0),
            (sp.Rational(1, 2), root / 2),
            (-sp.Rational(1, 2), root / 2),
            (-1, 0),
            (-sp.Rational(1, 2), -root / 2),
            (sp.Rational(1, 2), -root / 2),
        ],
    }[m.body]
    base = [sp.Matrix((x * a, y * a, 0)) for x, y in coordinates]
    center = sum(base, sp.zeros(3, 1)) / len(base)
    apex = center + sp.Matrix((0, 0, h))
    edge = norm(apex - base[0])
    slant = norm(apex - (base[0] + base[1]) / 2)
    base_area = area(base)
    lateral = sum(
        area([apex, p, base[(i + 1) % len(base)]]) for i, p in enumerate(base)
    )
    v = volume(apex, base)
    assert h > 0 and all(norm(apex - p) == edge for p in base)
    for symbol, amount in {
        "B": base_area,
        "P": len(base) * a,
        "l": slant,
        "e": edge,
        "V": v,
        "L": lateral,
        "S": base_area + lateral,
        "R": norm(base[0] - center),
        "r": norm((base[0] + base[1]) / 2 - center),
    }.items():
        if symbol in q:
            assert sp.simplify(q[symbol] - amount) == 0, (m.kind, symbol)
    actual = {
        "a": a,
        "H": h,
        "e": edge,
        "l": slant,
        "V": v,
        "L": lateral,
        "D": 2 * norm(base[0] - center),
    }
    inputs = {
        "square_total_edge": ("a", "e"),
        "hex_lateral_edge": ("a", "e"),
        "square_total_height": ("a", "H"),
        "square_lateral_height": ("a", "H"),
        "square_volume_height_edge": ("H", "e"),
        "square_volume_side_edge": ("e", "a"),
        "square_edge": ("H", "V"),
        "hex_volume_edge": ("a", "e"),
        "hex_edge": ("V", "a"),
        "triangle_lateral": ("a", "l"),
        "triangle_apothem": ("a", "L"),
        "triangle_side": ("l", "L"),
    }
    if m.kind in inputs:
        assert all(
            sp.simplify(actual[k] - g) == 0 for k, g in zip(inputs[m.kind], m.given)
        )
    points = {chr(65 + i): p for i, p in enumerate(base)}
    points["S"] = apex
    points["O"] = center
    values = {
        **q,
        "h": slant,
        "A": a * slant / 2,
        "p": len(base) * a / 2,
        r"\alpha": q.get("alpha", sp.Integer(45)),
    }
    if m.kind.startswith("named_"):
        for label, given in zip(m.names[:2], m.given):
            assert sp.simplify(norm(points[label[1]] - points[label[0]]) - given) == 0
        expected = norm(points[m.names[2][1]] - points[m.names[2][0]])
        for x, first in points.items():
            for y, second in points.items():
                if x != y:
                    values[x + y] = norm(second - first)
    elif m.kind in {"triangle_lateral", "triangle_apothem", "triangle_side"}:
        midpoint, edge_name, side_name, slant_name = m.names
        points[midpoint] = (points[edge_name[0]] + points[edge_name[1]]) / 2
        values[side_name] = norm(points[side_name[1]] - points[side_name[0]])
        values[slant_name] = norm(points["S"] - points[midpoint])
        expected = {
            "triangle_lateral": lateral,
            "triangle_apothem": slant,
            "triangle_side": a,
        }[m.kind]
    elif m.kind.endswith(("total_edge", "total_height")):
        expected = base_area + lateral
    elif m.kind in {"hex_lateral_edge", "square_lateral_height"}:
        expected = lateral
    elif m.kind in {"square_edge", "hex_edge"}:
        expected = edge
    else:
        expected = v
    if m.kind == "hex_face_angle":
        angle = m.given[1]
        normal = (apex - base[0]).cross(base[1] - base[0])
        assert (
            sp.simplify(sp.Abs(normal[2]) / norm(normal) - sp.cos(angle * sp.pi / 180))
            == 0
        )
    return values, sp.simplify(expected)


def basic(m):
    q = m.q
    if m.body == "rectangle":
        base = [
            sp.Matrix((0, 0, 0)),
            sp.Matrix((q["a"], 0, 0)),
            sp.Matrix((q["a"], q["b"], 0)),
            sp.Matrix((0, q["b"], 0)),
        ]
    else:
        side = sp.sqrt(4 * q["B"] / sp.sqrt(3))
        base = [
            sp.Matrix((0, 0, 0)),
            sp.Matrix((side, 0, 0)),
            sp.Matrix((side / 2, side * sp.sqrt(3) / 2, 0)),
        ]
    b = area(base)
    h = q["H"]
    v = volume(sp.Matrix((0, 0, h)), base)
    assert sp.simplify(b - q["B"]) == 0 and sp.simplify(v - q["V"]) == 0
    target = (
        "H" if m.kind.endswith("height") else "B" if m.kind == "center_area" else "V"
    )
    if m.kind.startswith("center_"):
        if target == "H":
            assert (b, v) == m.given
        elif target == "B":
            assert (v, h) == m.given
        else:
            assert (b, h) == m.given
    values = dict(q)
    return values, {"H": h, "B": b, "V": v}[target]


def other(m):
    q = m.q
    h = q["H"]
    if m.kind == "perpendicular":
        a = m.given[0]
        base = [sp.Matrix((0, 0, 0)), sp.Matrix((a, 0, 0)), sp.Matrix((0, a, 0))]
        apex = sp.Matrix((0, 0, a))
    elif m.kind == "floor":
        x, y, u, v = (q[k] for k in ("x", "y", "u", "v"))
        base = [
            sp.Matrix(p)
            for p in [
                (0, 0, 0),
                (x, 0, 0),
                (x, y - v, 0),
                (x - u, y - v, 0),
                (x - u, y, 0),
                (0, y, 0),
            ]
        ]
        apex = sp.Matrix((0, 0, h))
        b = sp.Abs(Polygon(*(Point2D(*p[:2]) for p in base)).area)
        assert b == q["B"]
        return dict(q), sp.simplify(b * h / 3)
    else:
        x, y = q["x"], q["y"]
        base = [sp.Matrix(p) for p in [(0, 0, 0), (x, 0, 0), (x, y, 0), (0, y, 0)]]
        apex = sp.Matrix((x / 2, 0, h))
        cosines = []
        for i, p in enumerate(base):
            normal = (apex - p).cross(base[(i + 1) % 4] - p)
            cosines.append(sp.simplify(sp.Abs(normal[2]) / norm(normal)))
        assert cosines.count(0) == 1 and cosines.count(sp.Rational(1, 2)) == 3
    assert area(base) == q["B"]
    return dict(q), volume(apex, base)
