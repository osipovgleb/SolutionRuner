"""Validate parent right-triangle and projection witnesses against exact named geometry."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from .orthogonal_element_geometry import VERTEX, answer, symbolic_points
from .orthogonal_element_sources import DATA, points


@dataclass(frozen=True)
class Element:
    kind: str
    given: dict
    points: dict
    symbolic: dict
    mode: str
    requested: str
    names: tuple
    method: str
    right: str | None
    value: sp.Expr


def perpendicular(vertices, a, r, b):
    u, v = vertices[a] - vertices[r], vertices[b] - vertices[r]
    return u.dot(u) > 0 and v.dot(v) > 0 and u.dot(v) == 0


def dimensions(vertices, a, b):
    return sum(v != 0 for v in vertices[a] - vertices[b])


def projection(vertices, names, kind):
    a, b = (vertices[n] for n in names[:2])
    if kind == "vertical":
        return sp.ImmutableMatrix((b[0], b[1], a[2]))
    if kind == "x_face":
        return sp.ImmutableMatrix((b[0], a[1], a[2]))
    if kind == "line":
        c = vertices[names[2]]
        direction = a - b
        if direction.dot(direction) == 0:
            raise ContentPlanError("the projected base line must be nonzero")
        return sp.ImmutableMatrix(
            b
            + sp.simplify((c - b).dot(direction) / direction.dot(direction)) * direction
        )
    raise ContentPlanError("the parent projection construction needs review")


def distance_right(vertices, names, method, kind):
    a, b = names
    if method == "projected_distance":
        return "K"
    if method == "ledge_distance":
        return "C_1"
    if kind == "elbow":
        return "C"
    candidates = [
        n for n in vertices if n not in names and perpendicular(vertices, a, n, b)
    ]
    if method == "face_distance":
        candidates = [
            n
            for n in candidates
            if dimensions(vertices, a, n) == dimensions(vertices, n, b) == 1
        ]
    elif method == "space_distance":
        candidates = [
            n
            for n in candidates
            if sorted((dimensions(vertices, a, n), dimensions(vertices, n, b)))
            == [1, 2]
            and (
                vertices[n][:2] == vertices[a][:2] or vertices[n][:2] == vertices[b][:2]
            )
        ]
    else:
        raise ContentPlanError("the distance parent method needs review")
    if not candidates:
        raise ContentPlanError("the named parent right triangle cannot be constructed")
    return max(candidates, key=lambda n: (vertices[n][2], n))


def angle_right(vertices, names):
    for right in names:
        a, b = (n for n in names if n != right)
        if perpendicular(vertices, a, right, b):
            if right == names[1]:
                break
            return right
    raise ContentPlanError("the parent needs an acute right-triangle angle")


def read(source, mode, requested, method):
    vertices = points(source)
    key = source + ":" + mode + ":" + requested
    review = DATA["proofs"].get(key)
    if not review or review["method"] != method:
        raise ContentPlanError("the complete named parent construction needs review")
    figure = DATA["figures"][source]
    symbolic = symbolic_points(figure["kind"], figure["given"])
    names = tuple(re.findall(VERTEX, requested))
    result = answer(vertices, mode, requested)
    if method in {"projected_distance", "projected_tangent"}:
        construction = tuple(review.get("projection_names", names))
        if set(construction) != set(names) or len(construction) != len(names):
            raise ContentPlanError(
                "the projection must use the actual requested vertices"
            )
        vertices["K"] = projection(vertices, construction, review["projection"])
        symbolic["K"] = projection(symbolic, construction, review["projection"])
    right = None
    if mode in {"distance", "distance_squared"}:
        right = distance_right(vertices, names, method, figure["kind"])
        if not perpendicular(vertices, names[0], right, names[1]):
            raise ContentPlanError("the parent distance triangle is not perpendicular")
    elif method == "projected_tangent":
        right = "K"
        a, b = (vertices[n] for n in names[:2])
        parameter = (vertices["K"] - b).dot(a - b) / (a - b).dot(a - b)
        if not 0 < parameter < 1 or not perpendicular(
            vertices, names[1], "K", names[2]
        ):
            raise ContentPlanError(
                "the tangent projection must lie inside the base segment"
            )
    elif method in {"face_tangent", "isosceles"}:
        right = angle_right(vertices, names)
    elif method != "equilateral":
        raise ContentPlanError("the requested quantity differs from its parent method")
    return Element(
        figure["kind"],
        figure["given"],
        vertices,
        symbolic,
        mode,
        requested,
        names,
        method,
        right,
        result,
    )
