"""Independent coordinates verify every numeric, vector and plane equality."""

import re

import sympy as sp
from bs4 import BeautifulSoup
from plane_geometry_oracle import foot

from solution_runner.pipelines.equations.trig_parser import TrigonometricParser
from solution_runner.pipelines.word_problems.common import UnsupportedCondition


def point_plane(p, a, b, c):
    normal = (b - a).cross(c - a)
    return sp.simplify(abs((p - a).dot(normal)) / normal.norm())


def pyramid(m):
    q = m.q
    a, h = q["a"], q["H"]
    extras = {}
    if m.mode.startswith("rectangular_pyramid"):
        b = q["b"]
        points = {
            "A": sp.zeros(3, 1),
            "B": sp.Matrix([a, 0, 0]),
            "C": sp.Matrix([a, b, 0]),
            "D": sp.Matrix([0, b, 0]),
            "S": sp.Matrix([0, 0, h]),
        }
        A, B, C, D, S = (points[n] for n in "ABCDS")
        assert (S - A).dot(B - A) == (S - A).dot(D - A) == 0
        if m.mode.endswith("angle"):
            u, v = C - S, B - S
            angle = sp.acos(u.dot(v) / (u.norm() * v.norm()))
            independent = sp.simplify(angle * 180 / sp.pi)
            extras.update(
                {
                    r"\tan\angle CSB": sp.simplify(u.cross(v).norm() / u.dot(v)),
                    r"\angle CSB": independent,
                }
            )
        else:
            independent = point_plane(A, S, B, C)
        extras[r"S_{ASB}"] = (B - A).cross(S - A).norm() / 2
    elif m.mode == "square_midplane_distance":
        points = {
            "A": sp.Matrix([-a / 2, -a / 2, 0]),
            "B": sp.Matrix([a / 2, -a / 2, 0]),
            "C": sp.Matrix([a / 2, a / 2, 0]),
            "D": sp.Matrix([-a / 2, a / 2, 0]),
            "S": sp.Matrix([0, 0, h]),
        }
        A, B, C, D, S = (points[n] for n in "ABCDS")
        points.update(M=(S + C) / 2, K=(S + B) / 2, N=(B + C) / 2, P=(A + D) / 2)
        points["Q"] = (S + points["N"]) / 2
        normal = (D - A).cross(points["M"] - A)
        assert sp.simplify((B - A).dot(normal) + (S - A).dot(normal)) == 0
        assert sp.simplify((points["Q"] - points["P"]).dot(S - points["N"])) == 0
        independent = point_plane(points[m.names[0]], A, D, points["M"])
    else:
        radius = a / sp.sqrt(3)
        points = {
            "A": sp.Matrix([radius, 0, 0]),
            "B": sp.Matrix([-radius / 2, a / 2, 0]),
            "C": sp.Matrix([-radius / 2, -a / 2, 0]),
            "S": sp.Matrix([0, 0, h]),
            "O": sp.zeros(3, 1),
        }
        A, B, C, S = (points[n] for n in "ABCS")
        points["M"] = (B + C) / 2
        points["H"] = foot(A, S, points["M"])
        assert sp.simplify((A - S).dot(B - C)) == 0
        if m.names[0] == "altitudes":
            T = sp.Matrix([0, 0, radius**2 / (2 * h)])
            assert sp.simplify((T - A).cross(points["H"] - A).norm()) == 0
            assert 0 < T[2] <= h
        independent = point_plane(A, S, B, C)
        extras.update(
            {
                "V": abs(sp.det(sp.Matrix.hstack(B - A, C - A, S - A))) / 6,
                r"S_{SBC}": (B - S).cross(C - S).norm() / 2,
            }
        )
    return points, extras, independent, None


def prism(m):
    q = m.q
    a, h, k, l = (q[n] for n in ("a", "H", "k", "l"))
    triangular = m.mode == "triangle_prism_section_distance"
    extras = {}
    if triangular:
        width = sp.sqrt(3) * a / 2
        points = {
            "A": sp.Matrix([-a / 2, width, 0]),
            "B": sp.zeros(3, 1),
            "C": sp.Matrix([a / 2, width, 0]),
        }
    else:
        points = {
            "A": sp.Matrix([a, a, 0]),
            "B": sp.Matrix([a, 0, 0]),
            "C": sp.zeros(3, 1),
            "D": sp.Matrix([0, a, 0]),
        }
    points.update({n + "_1": p + sp.Matrix([0, 0, h]) for n, p in list(points.items())})
    A, B, C = (points[n] for n in "ABC")
    if triangular:
        points.update(
            K=A + k / a * (B - A),
            K_1=C + k / a * (B - C),
            L=points["B_1"] + l / a * (points["C_1"] - points["B_1"]),
            L_1=points["B_1"] + l / a * (points["A_1"] - points["B_1"]),
        )
        points.update(N=(A + C) / 2, M=(points["A_1"] + points["C_1"]) / 2)
        points.update(
            E=(points["K"] + points["K_1"]) / 2, F=(points["L"] + points["L_1"]) / 2
        )
        points.update(T=points["N"], K_3=points["E"], L_3=points["F"])
        gap = abs(points["F"][1] - points["E"][1])
        extras.update(
            {
                r"\Delta": gap,
                r"\tan\varphi": h / gap,
                r"\tan\psi": h / width,
                "v": width,
            }
        )
    else:
        points.update(
            K=sp.Matrix([a - k, 0, 0]),
            K_1=sp.Matrix([0, a - k, 0]),
            L=sp.Matrix([0, l, h]),
        )
        points.update(
            E=sp.Matrix([(a - k) / 2, (a - k) / 2, 0]),
            F=sp.Matrix([l / 2, l / 2, h]),
            N=(A + C) / 2,
            M=(points["A_1"] + points["C_1"]) / 2,
        )
        start, end = (points[n] for n in re.findall(r"[A-Z](?:_1)?", m.names[0]))
        t, u = sp.symbols("t u")
        equations = (
            start + t * (end - start) - points["E"] - u * (points["F"] - points["E"])
        )
        solution = sp.solve((equations[0], equations[2]), (t, u))
        points["O"] = sp.simplify(start + solution[t] * (end - start))
    K, K1, L = (points[n] for n in ("K", "K_1", "L"))
    normal = (K1 - K).cross(L - K)
    start, end = (points[n] for n in re.findall(r"[A-Z](?:_1)?", m.names[0]))
    assert sp.simplify(normal.cross(end - start).norm()) == 0
    independent = point_plane(points[m.names[1]], K, K1, L)
    normal = sp.simplify(normal / normal[1])
    extras.update(
        a=a,
        c=sp.simplify(normal.dot(K)),
        n_z=normal[2],
        z_0=h if m.names[1] == "B_1" else 0,
    )
    return points, extras, independent, normal


def scalar(raw):
    return sp.simplify(TrigonometricParser(raw).parse().value)


def substitute(raw, values):
    for name, number in sorted(values.items(), key=lambda pair: -len(pair[0])):
        if name.startswith(("\\", "S_{")):
            raw = raw.replace(name, "(" + sp.latex(number) + ")")
        else:
            raw = re.sub(
                r"(?<![A-Za-z_])" + re.escape(name) + r"(?![A-Za-z_])",
                lambda _, v=number: "(" + sp.latex(v) + ")",
                raw,
            )
    raw = raw.replace(r"^{\circ}", "")
    return re.sub(
        r"\\left\|(.+?)\\right\|",
        lambda match: "(" + sp.latex(abs(scalar(match[1]))) + ")",
        raw,
    )


def verify(html, m):
    points, extra, answer, normal = (
        prism(m) if "prism_section" in m.mode else pyramid(m)
    )
    values = {
        a + b: sp.simplify((p - q).norm())
        for a, p in points.items()
        for b, q in points.items()
        if a != b
    }
    values.update(extra, d=answer, h=answer)
    for node in BeautifulSoup(html, "html.parser").select("[data-inline-latex]"):
        formula = node["data-inline-latex"]
        if formula.startswith(r"\vec n="):
            components = formula.split(r"\left(")[1].removesuffix(r"\right)").split(",")
            assert sp.simplify(
                sp.Matrix([scalar(x) for x in components]) - normal
            ) == sp.zeros(3, 1)
        elif formula.startswith(r"\overrightarrow{"):
            name, coefficient = formula.removeprefix(r"\overrightarrow{").split("}=", 1)
            a, b = re.findall(r"[A-Z](?:_1)?", name)
            assert sp.simplify(
                points[b]
                - points[a]
                - scalar(coefficient.removesuffix(r"\vec n")) * normal
            ) == sp.zeros(3, 1)
        else:
            evaluations = [values]
            if formula.startswith(("x+y+", "y+")):
                evaluations = [
                    values | dict(zip("xyz", points[n], strict=True))
                    for n in ("K", "K_1", "L")
                ]
            for data in evaluations:
                raw = substitute(formula, data)
                try:
                    sides = [scalar(side) for side in raw.split("=")]
                except UnsupportedCondition as exc:
                    raise AssertionError((formula, raw)) from exc
                assert len(sides) > 1 and all(
                    sp.simplify(v - sides[0]) == 0 for v in sides
                ), formula
    return answer
