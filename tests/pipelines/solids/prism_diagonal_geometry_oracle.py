"""Actual prism edges and spatial polygons independently check every equation."""

import sympy as sp
from altitude_geometry_oracle import scalar, substitute
from bs4 import BeautifulSoup
from plane_geometry_oracle import foot
from section_geometry_oracle import area


def polygon(points):
    total = sp.zeros(3, 1)
    for a, b in zip(points, points[1:] + points[:1]):
        total += a.cross(b)
    return sp.simplify(total.norm() / 2)


def square(m):
    given = dict(m.given)
    ratio_cut = m.mode == "square_prism_ratio_area"
    if ratio_cut:
        a, h = given["a"], given["height"]
    else:
        a = sp.sqrt(given["base"])
        h = (
            given["volume"] / given["base"]
            if "volume" in given
            else sp.sqrt(2 * (given["area"] ** 2 / given["base"] - given["base"]))
        )
    A, B, C, D = (sp.Matrix(v) for v in ((0, 0, 0), (a, 0, 0), (a, a, 0), (0, a, 0)))
    up = sp.Matrix([0, 0, h])
    points = dict(zip("ABCD", (A, B, C, D), strict=True))
    points.update({k + "_1": p + up for k, p in list(points.items())})
    extras = {"h": h, "V": a * a * h, "S_{ABCD}": a * a}
    if ratio_cut:
        t = given["q"] / (given["p"] + given["q"])
        if m.names == ("M",):
            points.update(M=sp.Matrix([0, t * a, h]), N=sp.Matrix([t * a, 0, h]))
            points["H"] = foot(points["N"], B, D)
            boundary = "BDMN"
        else:
            points.update(
                L=sp.Matrix([(1 - t) * a, a, h]), K=sp.Matrix([a, (1 - t) * a, h])
            )
            points["H"] = foot(points["L"], B, D)
            boundary = "BDLK"
        result = polygon([points[k] for k in boundary])
        extras["S_{" + boundary + "}"] = result
        return points, extras, result
    points.update(M=(A + points["A_1"]) / 2, K=(C + points["C_1"]) / 2)
    vertices = [points[k] for k in ("M", "B_1", "K", "D")]
    lengths = [
        sp.simplify((p - q).norm())
        for p, q in zip(vertices, vertices[1:] + vertices[:1])
    ]
    assert all(length == lengths[0] for length in lengths)
    result = polygon(vertices)
    if "area" in given:
        assert sp.simplify(result - given["area"]) == 0
    extras["S_{MB_1KD}"] = result
    return points, extras, result if m.mode.endswith("area") else h


def similarity(m):
    g = dict(m.given)
    small, large, volume, height = (
        g[k] for k in ("small", "large", "volume", "height")
    )
    ratio = small / large
    r = volume / (2 * height * large)
    B = sp.zeros(3, 1)
    A, N = sp.Matrix([-large / 2, -r, 0]), sp.Matrix([large / 2, -r, 0])
    C = 2 * N
    D = A + C
    points = {"A": A, "B": B, "C": C, "D": D, "N": N}
    up = sp.Matrix([0, 0, height])
    points.update({k + "_1": points[k] + up for k in "ABCD"})
    M, K = ratio * A + up, ratio * N + up
    points.update(M=M, K=K, H=foot(B, A, N), H_1=foot(up, M, K))
    assert sp.simplify((K - up).norm() / (C + up - K).norm() - g["p"] / g["q"]) == 0
    base = polygon([A, B, C, D])
    assert sp.simplify(base * height - volume) == 0
    result = polygon([A, M, K, N])
    return (
        points,
        {
            "k": ratio,
            "S_{ABCD}": base,
            "S_{ABN}": area(A, B, N),
            "S_{MB_1K}": area(M, up, K),
            "S_{AMKN}": result,
            "h": height,
            "V": volume,
        },
        result,
    )


def _pentagon_boundary(base, upper, normal, origin, vertices):
    edges = (
        list(zip(base, base[1:] + base[:1]))
        + list(zip(upper, upper[1:] + upper[:1]))
        + list(zip(base, upper))
    )
    hits = []
    for p, q in edges:
        f0, f1 = (sp.simplify(normal.dot(v - origin)) for v in (p, q))
        if f0 == f1:
            assert f0 != 0
            continue
        t = sp.simplify(-f0 / (f1 - f0))
        if 0 <= t <= 1:
            hit = sp.simplify(p + t * (q - p))
            if not any(hit == old for old in hits):
                hits.append(hit)
    assert len(hits) == 5
    assert all(any(p == q for q in hits) for p in vertices)


def pentagon(m):
    g = dict(m.given)
    a, b = g["a"], g["b"]
    d = a - b
    y = d * sp.sqrt(3) / 2
    z = sp.sqrt(b * d / 2)
    A, B, C, D = (
        sp.Matrix([0, 0, 0]),
        sp.Matrix([d / 2, y, 0]),
        sp.Matrix([a - d / 2, y, 0]),
        sp.Matrix([a, 0, 0]),
    )
    up = sp.Matrix([0, 0, 2 * z])
    P, T, N = sp.Matrix([d, 0, 2 * z]), sp.Matrix([a, 0, z]), B + up / 2
    normal = (T - P).cross(C - P)
    assert sp.simplify(normal.dot(N - P)) == 0 and sp.simplify((P - T).dot(C - T)) == 0
    u = sp.symbols("u")
    L = u * B + up
    fraction = sp.solve(normal.dot(L - P), u)[0]
    assert 0 < fraction < 1
    L = sp.simplify(L.subs(u, fraction))
    base = [A, B, C, D]
    vertices = [C, T, P, L, N]
    _pentagon_boundary(base, [v + up for v in base], normal, P, vertices)
    p, k = m.names
    points = dict(zip("ABCD", base, strict=True))
    points.update({key + "_1": points[key] + up for key in "ABCD"})
    points.update({p: P, k: T, "N": N, "L": L, "H": foot(C, A, D), p + "_1": P - up})
    E = P - P[0] / (T[0] - P[0]) * (T - P)
    points["E"] = sp.simplify(E)
    result = polygon(vertices)
    extras = {
        "S_{C" + k + p + "LN}": result,
        "S_{C" + k + p + "N}": polygon([C, T, P, N]),
        "S_{" + p + "LN}": area(P, L, N),
        "S_{E" + p + "N}": area(E, P, N),
    }
    return points, extras, result


def verify(html, m):
    if m.mode == "trapezoid_prism_pentagon_area":
        points, extras, answer = pentagon(m)
    elif m.mode == "parallelogram_prism_trapezoid_area":
        points, extras, answer = similarity(m)
    else:
        points, extras, answer = square(m)
    values = {
        a + b: sp.simplify((A - B).norm())
        for a, A in points.items()
        for b, B in points.items()
        if a != b
    }
    values.update(extras)
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        formula = (
            formula.replace(r"\cos60^\circ", r"(\frac{1}{2})")
            .replace(r"\sin60^\circ", r"(\frac{\sqrt{3}}{2})")
            .replace(r"\cos120^\circ", r"(-\frac{1}{2})")
        )
        formula = formula.replace(r"\frac12", r"\frac{1}{2}")
        for expression in formula.split(r",\qquad "):
            raw = substitute(expression, values)
            try:
                sides = [scalar(side) for side in raw.split("=")]
            except Exception as exc:
                raise AssertionError((formula, raw)) from exc
            assert len(sides) > 1 and all(
                sp.simplify(v - sides[0]) == 0 for v in sides
            ), (formula, sides)
    return sp.simplify(answer)
