"""Exact relations between inscribed solids and the quantities actually requested."""

from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from .measurements import positive


@dataclass(frozen=True)
class Combination:
    kind: str
    given: tuple[sp.Expr, ...]
    answer: sp.Expr
    q: dict[str, sp.Expr]


def result(kind, given, answer, **quantities):
    answer = sp.simplify(answer)
    if answer.is_positive is not True or answer.is_finite is not True:
        raise ContentPlanError(
            "the combined solid quantity must be positive and finite"
        )
    return Combination(kind, given, answer, quantities)


def ratio(kind, raw=None):
    factors = {
        "sphere_cylinder_surface": sp.Rational(2, 3),
        "cylinder_sphere_surface": sp.Rational(3, 2),
        "sphere_cylinder_volume": sp.Rational(2, 3),
        "cylinder_sphere_volume": sp.Rational(3, 2),
        "cylinder_cone_volume": sp.Integer(3),
        "cone_cylinder_volume": sp.Rational(1, 3),
        "cone_sphere_volume": sp.Rational(1, 4),
        "sphere_cone_volume": sp.Integer(4),
        "pyramid_cones_ratio": sp.Integer(2),
        "pyramid_outer_cone_volume": sp.Integer(2),
        "pyramid_inner_cone_volume": sp.Rational(1, 2),
        "tetra_midpoint_volume": sp.Rational(1, 2),
        "tetra_midpoint_surface": sp.Rational(1, 2),
        "cone_cylinder_lateral": sp.sqrt(2) / 2,
    }
    factor = factors[kind]
    given = () if raw is None else (positive(raw),)
    return result(kind, given, factor * (given[0] if given else 1), factor=factor)


def cube(kind, raw):
    x = positive(raw, pi=True)
    if kind == "cube_sphere_volume":
        if not x.has(sp.pi) or (x / sp.pi).has(sp.pi):
            raise ContentPlanError("the ball volume needs an explicit pi coefficient")
        r3 = 3 * x / (4 * sp.pi)
        return result(kind, (x,), 8 * r3, r3=r3)
    if x.has(sp.pi):
        raise ContentPlanError("this cube dimension must not contain pi")
    if kind == "cube_insphere_radius":
        a = x ** sp.Rational(1, 3)
    elif kind in {"cube_around_sphere_volume", "cube_around_sphere_surface"}:
        a = 2 * x
    elif kind == "cube_in_sphere_volume":
        a = 2 * x / sp.sqrt(3)
    else:
        a = x
    a = sp.simplify(a)
    r = a * sp.sqrt(3) / 2 if kind == "cube_circumsphere_volume" else a / 2
    answers = {
        "cube_insphere_radius": r,
        "cube_around_sphere_volume": a**3,
        "cube_around_sphere_surface": 6 * a**2,
        "cube_in_sphere_volume": a**3,
        "cube_insphere_volume": 4 * r**3 / 3,
        "cube_circumsphere_volume": 4 * r**3 / 3,
    }
    return result(kind, (x,), answers[kind], a=a, r=sp.simplify(r))


def prism(kind, raw):
    g = tuple(positive(s) for s in raw)
    r, x = g
    if kind == "box_cylinder_volume":
        h, a = x, 2 * r
        return result(kind, g, a**2 * h, r=r, a=a, H=h, B=a**2)
    if kind == "box_cylinder_height":
        a, h = 2 * r, x / (4 * r**2)
        return result(kind, g, h, r=r, a=a, H=sp.simplify(h), B=a**2)
    sides, coefficient = {
        "square_cylinder_lateral": (4, 2),
        "triangle_around_cylinder_lateral": (3, 2 * sp.sqrt(3)),
        "triangle_in_cylinder_lateral": (3, sp.sqrt(3)),
        "hexagon_cylinder_lateral": (6, 2 / sp.sqrt(3)),
        "square_cylinder_height": (4, 2),
    }[kind]
    a = sp.simplify(coefficient * r)
    p = sp.simplify(sides * a)
    h = sp.simplify(x / p) if kind == "square_cylinder_height" else x
    return result(kind, g, h if kind.endswith("height") else p * h, r=r, a=a, P=p, H=h)


def cylinder_around_prism(kind, raw):
    # These parents give height as an explicit quotient with denominator pi.
    g = tuple(positive(s) for s in raw)
    *base, coefficient = g
    d2 = sum(a**2 for a in base) if len(base) == 2 else 2 * base[0] ** 2
    return result(kind, g, d2 * coefficient / 4, d2=d2, H=coefficient / sp.pi)


def cone_sphere(kind, raw):
    x = positive(raw)
    r = sp.simplify(x / sp.sqrt(2)) if kind == "cone_sphere_radius" else x
    l = sp.simplify(r * sp.sqrt(2))
    return result(kind, (x,), r if kind == "cone_sphere_radius" else l, r=r, H=r, l=l)


def pyramid_cone(raw):
    a, h = g = tuple(positive(s) for s in raw)
    r = sp.simplify(a / sp.sqrt(2))
    return result("pyramid_cone_volume", g, a**2 * h / 6, a=a, H=h, r=r)


def sphere_part(kind, raw):
    g = tuple(positive(s) for s in raw)
    a = g[0]
    r = a if kind == "sphere_vertex_part" else g[1]
    fraction = sp.Rational(1, 8) if kind == "sphere_vertex_part" else sp.Rational(1, 4)
    if kind == "sphere_edge_part" and (a / 2 - r).is_nonnegative is not True:
        raise ContentPlanError("the sphere reaches beyond the cube's end faces")
    return result(kind, g, 4 * fraction * r**2, a=a, r=r, fraction=fraction)


def cube_hole(raw):
    b, h = g = tuple(positive(s) for s in raw)
    if h != 1 or (1 - b).is_positive is not True:
        raise ContentPlanError(
            "the reviewed internal through-hole needs unit height and side below one"
        )
    return result("cube_prism_hole", g, 6 + 4 * b * h - 2 * b**2, a=sp.S.One, b=b, H=h)
