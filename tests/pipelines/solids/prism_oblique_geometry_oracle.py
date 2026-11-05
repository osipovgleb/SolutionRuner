"""Independent prism coordinates check scalar, vector and plane equations."""

import re

import sympy as sp
from altitude_geometry_oracle import scalar, substitute
from bs4 import BeautifulSoup
from prism_diagonal_geometry_oracle import polygon
from section_geometry_oracle import area


def oblique(m):
    g = dict(m.given)
    a, Q = g["a"], g["area"]
    h = sp.sqrt(16 * Q * Q / (3 * a * a) - a * a)
    points = {
        "A": sp.zeros(3, 1),
        "B": sp.Matrix([a, 0, 0]),
        "C": sp.Matrix([a / 2, a * sp.sqrt(3) / 2, 0]),
    }
    up = sp.Matrix([0, 0, h])
    points.update({k + "_1": v + up for k, v in list(points.items())})
    points.update(M=points["C"] + up / 2, O=(points["A_1"] + points["B"]) / 2)
    assert (
        sp.simplify((points["M"] - points["O"]).dot(points["A_1"] - points["B"])) == 0
    )
    actual = area(points["A_1"], points["M"], points["B"])
    assert sp.simplify(actual - Q) == 0
    return points, {"x": h / 2, "S_{A_1MB}": actual}, h


def perpendicular(m):
    g = dict(m.given)
    k = g["coefficient"]
    r = k / (k + 1) if m.names[1] == "AM" else 1 / (k + 1)
    a = g.get("a")
    if a is None:
        a = sp.sqrt(
            4 * g["area"] / (sp.sqrt(3) * sp.sqrt((1 - r) ** 2 + sp.Rational(1, 4)))
        )
    a = sp.simplify(a)
    A, B, C = (
        sp.zeros(3, 1),
        sp.Matrix([a * sp.sqrt(3) / 2, a / 2, 0]),
        sp.Matrix([0, a, 0]),
    )
    up = sp.Matrix([0, 0, a])
    points = {
        "A": A,
        "B": B,
        "C": C,
        "A_1": A + up,
        "B_1": B + up,
        "C_1": C + up,
        "M": r * up,
        "K": (A + B) / 2 + up,
    }
    n = (points["K"] - points["M"]).cross(points["C_1"] - points["M"])
    face = B.cross(up)
    assert sp.simplify(n.dot(face)) == 0
    assert (
        sp.simplify((points["C_1"] - points["K"]).dot(points["K"] - points["M"])) == 0
    )
    actual = area(points["M"], points["K"], points["C_1"])
    if "area" in g:
        assert sp.simplify(actual - g["area"]) == 0
    return (
        points,
        {
            "a": a,
            "b": a,
            "u": a,
            "S_{MKC_1}": actual,
            "N_x": sp.sqrt(3) * a * (1 - r),
            "N_y": a * (1 - r),
            "N_z": -a,
            "d": r * a * a,
        },
        a if m.mode.endswith("height") else actual,
    )


def box(m):
    g = dict(m.given)
    a, b, h = g["a"], g["b"], g["height"]
    up = sp.Matrix([0, 0, h])
    points = {
        "A": sp.zeros(3, 1),
        "B": sp.Matrix([a, 0, 0]),
        "C": sp.Matrix([a, b, 0]),
        "D": sp.Matrix([0, b, 0]),
    }
    points.update({k + "_1": p + up for k, p in list(points.items())})
    if m.mode == "box_opposite_section_area":
        low = h * g["p"] / (g["p"] + g["q"])
        if m.names[0] == "W":
            points.update(
                W=points["D"] + sp.Matrix([0, 0, low]),
                T=points["B"] + sp.Matrix([0, 0, h - low]),
            )
            vertices = [points[k] for k in ("C", "T", "A_1", "W")]
            name = "CTA_1W"
        else:
            points.update(
                O=points["B"] + sp.Matrix([0, 0, low]),
                P=points["D"] + sp.Matrix([0, 0, h - low]),
            )
            vertices = [points[k] for k in ("A", "O", "C_1", "P")]
            name = "AOC_1P"
        normal = (vertices[1] - vertices[0]).cross(vertices[3] - vertices[0])
        assert sp.simplify(normal.dot(vertices[2] - vertices[0])) == 0
        assert vertices[0] + vertices[2] == vertices[1] + vertices[3]
        d1 = vertices[2] - vertices[0]
        d2 = (
            vertices[1] - vertices[3]
            if m.names[0] == "W"
            else vertices[3] - vertices[1]
        )
        actual = polygon(vertices)
        return (
            points,
            {
                "S_{" + name + "}": actual,
                r"\cos\varphi": sp.simplify(d1.dot(d2) / (d1.norm() * d2.norm())),
            },
            actual,
        )
    M = points["C_1"] / 2
    normal = points["C_1"]
    t = sp.simplify(-normal.dot(up - M) / normal.dot(points["B"]))
    T = up + t * points["B"]
    K = up + sp.simplify(-normal.dot(up - M) / normal.dot(points["C"])) * points["C"]
    points.update(M=M, T=T, K=K)
    for name in ("D_1", "B", "T", "K"):
        assert sp.simplify(normal.dot(points[name] - M)) == 0
    assert sp.simplify((T - K).cross(points["D_1"] - K).norm()) == 0
    return points, {"t": t, "u": a * (1 - t)}, sp.simplify(t / (1 - t))


def canonical(raw):
    for old, new in (
        (r"\frac12", r"\frac{1}{2}"),
        (r"\frac14", r"\frac{1}{4}"),
        (r"\sqrt3", r"\sqrt{3}"),
        (r"\frac a2", r"\frac{a}{2}"),
        (r"\frac a4", r"\frac{a}{4}"),
    ):
        raw = raw.replace(old, new)
    for product in ("ab", "bx", "by", "az"):
        raw = raw.replace(product, product[0] + r"\cdot " + product[1])
    return raw.replace("bN_z", r"b\cdot N_z")


def evaluate(raw, values):
    return scalar(substitute(canonical(raw), values))


def vector(name, points):
    labels = re.findall(r"[A-Z](?:_1)?", name)
    assert len(labels) == 2 and "".join(labels) == name, name
    return points[labels[1]] - points[labels[0]]


def _coordinates(formula, points, values):
    if formula.startswith((r"\vec n_{\alpha}=", r"\vec n_{\beta}=")):
        components = formula.split("=(", 1)[1][:-1].split(";")
        n = sp.Matrix([evaluate(c, values) for c in components])
        face = (points["B"] - points["A"]).cross(points["A_1"] - points["A"])
        assert sp.simplify(n.dot(face)) == 0
        for key in ("K", "C_1"):
            assert sp.simplify(n.dot(points[key] - points["M"])) == 0
        return True
    if re.match(r"[A-Z](?:_1)?\(", formula):
        for part in formula.split(r"\quad "):
            match = re.fullmatch(r"([A-Z](?:_1)?)\((.+)\)", part.strip().strip(","))
            assert match, formula
            actual = sp.Matrix([evaluate(c, values) for c in match[2].split(";")])
            assert sp.simplify(actual - points[match[1]]) == sp.zeros(3, 1), (
                formula,
                actual,
                points[match[1]],
            )
        return True
    return False


def _vector_equations(formula, points, values):
    if r"\overrightarrow" not in formula:
        return False
    if formula.startswith(r"\left|"):
        v, w = vector("C_1K", points), vector("C_1M", points)
        _left, right = formula.split("=", 1)
        assert sp.simplify(v.cross(w).norm() - evaluate(right, values)) == 0
        return True
    pieces = formula.split(r",\quad ")
    for part in pieces:
        match = re.fullmatch(
            r"\\overrightarrow\{([^}]+)\}(?:\\times\\overrightarrow\{([^}]+)\})?=\((.+)\)",
            part,
        )
        if match:
            actual = vector(match[1], points)
            if match[2]:
                actual = actual.cross(vector(match[2], points))
            stated = sp.Matrix([evaluate(c, values) for c in match[3].split(";")])
            assert sp.simplify(stated - actual) == sp.zeros(3, 1), part
            continue
        raw = re.sub(
            r"\\overrightarrow\{([^}]+)\}\\cdot\\overrightarrow\{([^}]+)\}",
            lambda x: (
                "(" + sp.latex(vector(x[1], points).dot(vector(x[2], points))) + ")"
            ),
            part,
        )
        for axis in range(3):
            expanded = re.sub(
                r"\\overrightarrow\{([^}]+)\}",
                lambda x, axis=axis: "(" + sp.latex(vector(x[1], points)[axis]) + ")",
                raw,
            )
            sides = [evaluate(v, values) for v in expanded.split("=")]
            assert all(sp.simplify(v - sides[0]) == 0 for v in sides), part
    return True


def verify(html, m):
    if m.mode == "triangle_prism_oblique_height":
        points, extra, answer = oblique(m)
    elif m.mode.startswith("triangle_prism_perpendicular"):
        points, extra, answer = perpendicular(m)
    else:
        points, extra, answer = box(m)
    values = {
        a + b: sp.simplify((A - B).norm())
        for a, A in points.items()
        for b, B in points.items()
        if a != b
    }
    values.update(extra)
    coordinate = False
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        frame = points
        if m.mode == "box_diagonal_bisector_ratio" and formula.startswith("A("):
            coordinate = True
        if coordinate:
            frame = {
                k: sp.Matrix([dict(m.given)["a"] - p[0], p[1], p[2]])
                for k, p in points.items()
            }
        if _coordinates(formula, frame, values) or _vector_equations(
            formula, frame, values
        ):
            continue
        expressions = (
            formula[len(r"\begin{cases}") : -len(r"\end{cases}")].split(r"\\")
            if formula.startswith(r"\begin{cases}")
            else formula.split(r",\qquad ")
        )
        for expression in expressions:
            evaluations = [values]
            if (
                re.search(r"[xyz]", re.sub(r"\\[A-Za-z]+", "", expression))
                and m.mode != "triangle_prism_oblique_height"
            ):
                names = (
                    ("M", "K", "C_1")
                    if m.mode.startswith("triangle_prism_perpendicular")
                    else ("M", "T", "D_1")
                )
                evaluations = [
                    values | dict(zip("xyz", frame[key], strict=True)) for key in names
                ]
            for data in evaluations:
                try:
                    sides = [evaluate(part, data) for part in expression.split("=")]
                except Exception as exc:
                    raise AssertionError((formula, expression)) from exc
                assert len(sides) > 1 and all(
                    sp.simplify(v - sides[0]) == 0 for v in sides
                ), (formula, sides)
    return sp.simplify(answer)
