"""Recognize geometric volume witnesses among actual parallelepiped vertices."""

import itertools
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from .box_coordinates import VERTICES


def vertex(point):
    return next(name for name, p in VERTICES.items() if p == tuple(point))


def face_order(names, axis):
    directions = [i for i in range(3) if i != axis]
    order = {(0, 0): 0, (1, 0): 1, (1, 1): 2, (0, 1): 3}
    return tuple(
        sorted(names, key=lambda n: order[tuple(VERTICES[n][i] for i in directions)])
    )


@dataclass(frozen=True)
class Polyhedron:
    vertices: tuple[str, ...]
    kind: str
    fraction: sp.Rational
    base: tuple[str, ...] = ()
    upper: tuple[str, ...] = ()
    axis: int | None = None
    apex: str | None = None
    foot: str | None = None

    @property
    def faces(self):
        if self.kind == "central_tetrahedron":
            return tuple(itertools.combinations(self.vertices, 3))
        pairs = tuple(zip(self.base, self.base[1:] + self.base[:1]))
        if self.kind == "pyramid":
            return (self.base, *((a, b, self.apex) for a, b in pairs))
        return (
            self.base,
            self.upper,
            *(
                (
                    self.base[i],
                    self.base[(i + 1) % 3],
                    self.upper[(i + 1) % 3],
                    self.upper[i],
                )
                for i in range(3)
            ),
        )


def _pyramid(names, preferred_axis=None):
    axes = (
        (2, 0, 1)
        if preferred_axis is None
        else (preferred_axis, *(i for i in (2, 0, 1) if i != preferred_axis))
    )
    for axis, level in itertools.product(axes, (0, 1)):
        base = tuple(n for n in names if VERTICES[n][axis] == level)
        if len(base) != len(names) - 1:
            continue
        apex = next(n for n in names if n not in base)
        point = list(VERTICES[apex])
        point[axis] = level
        return Polyhedron(
            names,
            "pyramid",
            sp.Rational(1, 6 if len(base) == 3 else 3),
            face_order(base, axis),
            axis=axis,
            apex=apex,
            foot=vertex(point),
        )
    if len(names) == 4:
        outside = set(VERTICES) - set(names)
        if all(
            sum(
                sum(abs(x - y) for x, y in zip(VERTICES[a], VERTICES[b])) == 1
                for b in names
            )
            == 3
            for a in outside
        ):
            return Polyhedron(names, "central_tetrahedron", sp.Rational(1, 3))
    raise ContentPlanError(
        "the vertices do not yield a reviewed pyramid volume witness"
    )


def _prism(names):
    for axis in range(3):
        base = tuple(n for n in names if VERTICES[n][axis] == 0)
        if len(base) != 3:
            continue
        base = face_order(base, axis)
        upper = []
        for name in base:
            point = list(VERTICES[name])
            point[axis] = 1
            upper.append(vertex(point))
        if set(base) | set(upper) == set(names):
            return Polyhedron(
                names, "prism", sp.Rational(1, 2), base, tuple(upper), axis
            )
    raise ContentPlanError("the six vertices must form a triangular prism of the box")


def recognize(names, *, preferred_axis=None):
    if (
        not isinstance(names, (tuple, list))
        or len(names) not in (4, 5, 6)
        or any(n not in VERTICES for n in names)
        or len(set(names)) != len(names)
    ):
        raise ContentPlanError(
            "four, five or six distinct canonical solid vertices are required"
        )
    if preferred_axis is not None and preferred_axis not in (0, 1, 2):
        raise ContentPlanError("a canonical parent height axis is required")
    ordered = tuple(n for n in VERTICES if n in names)
    return _prism(ordered) if len(ordered) == 6 else _pyramid(ordered, preferred_axis)
