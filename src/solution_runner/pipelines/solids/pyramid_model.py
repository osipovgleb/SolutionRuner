"""Exact pyramid dimensions from common base, height, edge and apothem relations."""

from dataclasses import dataclass, field

import sympy as sp

from ..core.errors import ContentPlanError
from .measurements import positive

BASES = {
    "triangle": (3, sp.sqrt(3) / 4, sp.sqrt(3) / 3, sp.sqrt(3) / 6),
    "square": (4, sp.S.One, sp.sqrt(2) / 2, sp.Rational(1, 2)),
    "hexagon": (6, 3 * sp.sqrt(3) / 2, sp.S.One, sp.sqrt(3) / 2),
}


@dataclass(frozen=True)
class Pyramid:
    kind: str
    given: tuple[sp.Expr, ...]
    answer: sp.Expr
    body: str = ""
    q: dict[str, sp.Expr] = field(default_factory=dict)
    names: tuple[str, ...] = ()
    symbols: dict[str, str] = field(default_factory=dict)


def root(value):
    value = sp.simplify(value)
    if value.is_positive is not True:
        raise ContentPlanError(
            "the pyramid dimensions must define a nondegenerate solid"
        )
    return sp.sqrt(value)


def regular(body, known):
    n, k, circum, inradius = BASES[body]
    q = {key: sp.simplify(value) for key, value in known.items()}
    if "a" not in q:
        if {"H", "e"} <= q.keys():
            q["a"] = root(q["e"] ** 2 - q["H"] ** 2) / circum
        elif {"V", "H"} <= q.keys():
            q["a"] = root(3 * q["V"] / q["H"] / k)
        elif {"D", "H"} <= q.keys() or {"D", "e"} <= q.keys():
            q["a"] = q["D"] / 2 / circum
        elif {"l", "L"} <= q.keys():
            q["a"] = 2 * q["L"] / (n * q["l"])
        else:
            raise ContentPlanError("independent pyramid dimensions are required")
    a = q["a"]
    q.update(B=k * a * a, P=n * a, R=circum * a, r=inradius * a, D=2 * circum * a)
    if "H" not in q:
        if "e" in q:
            q["H"] = root(q["e"] ** 2 - q["R"] ** 2)
        elif "V" in q:
            q["H"] = 3 * q["V"] / q["B"]
        elif "l" in q:
            q["H"] = root(q["l"] ** 2 - q["r"] ** 2)
        elif "L" in q:
            q["l"] = 2 * q["L"] / q["P"]
            q["H"] = root(q["l"] ** 2 - q["r"] ** 2)
        else:
            raise ContentPlanError("the pyramid height needs independent data")
    q.update(e=root(q["H"] ** 2 + q["R"] ** 2), l=root(q["H"] ** 2 + q["r"] ** 2))
    q.update(V=q["B"] * q["H"] / 3, L=q["P"] * q["l"] / 2)
    q["S"] = q["B"] + q["L"]
    q = {key: sp.simplify(value) for key, value in q.items()}
    if any(value.is_positive is not True for value in q.values()):
        raise ContentPlanError("positive pyramid dimensions are required")
    return q


def measured(kind, body, given, fields, target, names=()):
    values = tuple(positive(v) for v in given)
    q = regular(body, dict(zip(fields, values)))
    return Pyramid(kind, values, q[target], body, q, names)


def base_volume(kind, given, shape, target, names=()):
    values = tuple(positive(v) for v in given)
    if shape == "rectangle":
        a, b, last = values
        area = a * b
    elif shape == "triangle":
        a, last = values
        area = sp.sqrt(3) * a * a / 4
    else:
        area, last = values
        a = root(4 * area / sp.sqrt(3))
    if target == "V":
        height = last
        volume = area * height / 3
    else:
        volume = last
        height = 3 * volume / area
    q = {"B": area, "H": height, "V": volume, "a": a}
    if shape == "rectangle":
        q["b"] = b
    return Pyramid(
        kind,
        values,
        sp.simplify(q[target]),
        "triangle" if shape == "area" else shape,
        {k: sp.simplify(v) for k, v in q.items()},
        names,
    )


def center_area(given, names):
    volume, height = (positive(v) for v in given)
    area = 3 * volume / height
    return Pyramid(
        "center_area",
        (volume, height),
        area,
        "triangle",
        {"B": area, "V": volume, "H": height},
        names,
    )


def perpendicular(given):
    a = positive(given[0])
    area = a * a / 2
    volume = area * a / 3
    return Pyramid(
        "perpendicular",
        (a,),
        volume,
        "trihedral",
        {"a": a, "B": area, "H": a, "V": volume},
    )


def face_angle(body, given):
    a, angle = (positive(v) for v in given)
    if angle not in {30, 45, 60}:
        raise ContentPlanError("a reviewed acute dihedral angle is required")
    r = BASES[body][3] * a
    height = r * sp.tan(sp.pi * angle / 180)
    q = regular(body, {"a": a, "H": height})
    q["alpha"] = angle
    return Pyramid("hex_face_angle", (a, angle), q["V"], body, q)


def perpendicular_face(given):
    angle, height = (positive(v) for v in given)
    if angle != 60:
        raise ContentPlanError(
            "the perpendicular-face parent uses three 60-degree faces"
        )
    width = 2 * height / sp.sqrt(3)
    depth = height / sp.sqrt(3)
    area = width * depth
    volume = area * height / 3
    return Pyramid(
        "perpendicular_face",
        (angle, height),
        sp.simplify(volume),
        "rectangle",
        {
            "H": height,
            "x": width,
            "y": depth,
            "B": sp.simplify(area),
            "V": sp.simplify(volume),
        },
    )
