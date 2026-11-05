"""Prove surface identities using exposed faces, exact contacts and complete partitions."""

from itertools import combinations, product

import sympy as sp

from ..core.errors import ContentPlanError
from .orthogonal_geometry import Cuboid, OrthogonalSolid
from .orthogonal_shapes import block


def bounding(m):
    return Cuboid(tuple(a[0] for a in m.solid.axes), tuple(a[-1] for a in m.solid.axes))


def missing_box(m):
    axes = m.solid.axes
    absent = set(product(*(range(len(a) - 1) for a in axes))) - m.solid.cells
    if not absent:
        raise ContentPlanError("a reviewed rectangular cut is required")
    cut = Cuboid(
        tuple(axes[i][min(c[i] for c in absent)] for i in range(3)),
        tuple(axes[i][max(c[i] for c in absent) + 1] for i in range(3)),
    )
    if not OrthogonalSolid((bounding(m),), (cut,)).equivalent(m.solid):
        raise ContentPlanError("the removed region is not the claimed rectangular cut")
    return cut


def contact_dimensions(a, b):
    spans = tuple(
        min(x, y) - max(u, v) for x, y, u, v in zip(a.upper, b.upper, a.lower, b.lower)
    )
    if any(s < 0 for s in spans) or sum(s == 0 for s in spans) != 1:
        return ()
    return tuple(s for s in spans if s != 0)


def contact(a, b):
    sizes = contact_dimensions(a, b)
    return sp.prod(sizes) if sizes else sp.S.Zero


def partition(m, parts):
    union = OrthogonalSolid(parts)
    if union.volume != sum(p.volume for p in parts) or not union.equivalent(m.solid):
        raise ContentPlanError("the surface parts do not partition the actual material")
    shared = sum(contact(a, b) for a, b in combinations(parts, 2))
    if sum(p.surface for p in parts) - 2 * shared != m.solid.surface:
        raise ContentPlanError(
            "the exposed-area identity differs from the solid boundary"
        )
    return shared


def corner(m):
    box, cut = bounding(m), missing_box(m)
    x, y, z = box.dimensions
    if m.solid.directed_areas != (y * z, y * z, x * z, x * z, x * y, x * y):
        raise ContentPlanError(
            "this corner does not preserve the three projected face pairs"
        )
    return box, cut


def glued_parts(m, style):
    if style == "shelf_both":
        parts = tuple(reversed(m.parts))
    elif style == "glued_three":
        base, top, side = m.solid.additions
        tall = Cuboid((top.lower[0], top.lower[1], base.lower[2]), top.upper)
        front = block(
            (base.dimensions[0], top.lower[1] - base.lower[1], base.dimensions[2]),
            base.lower,
        )
        parts = (tall, front, side)
    else:
        parts = m.parts
    shared = partition(m, parts)
    return parts, shared


def central_cancellation(m):
    base, side, top = m.solid.additions
    central = Cuboid(
        (top.lower[0], top.lower[1], base.lower[2]),
        (top.upper[0], top.upper[1], top.lower[2]),
    )
    front = block(
        (base.dimensions[0], top.lower[1] - base.lower[1], base.dimensions[2]),
        base.lower,
    )
    parts = (top, front, side)
    partition(m, (central, *parts))
    shared = sum(contact(central, p) for p in parts)
    if (
        central.surface != 2 * shared
        or sum(p.surface for p in parts) != m.solid.surface
    ):
        raise ContentPlanError(
            "the central block's faces do not cancel the internal contacts"
        )
    return central, parts, shared
