"""Exact union, cutout and exposed-face measures on a bounded rectangular cell grid."""

from dataclasses import dataclass, field
from itertools import product

import sympy as sp

from ..core.errors import ContentPlanError
from ..equations.power_arithmetic import rational
from ..probability.common import UnsupportedCondition


def coordinate(raw):
    if isinstance(raw, bool) or not isinstance(raw, (int, str, sp.Rational)):
        raise ContentPlanError("an exact bounded rational coordinate is required")
    try:
        return rational(str(raw))
    except (ValueError, ZeroDivisionError, UnsupportedCondition) as exc:
        raise ContentPlanError(
            "an exact bounded rational coordinate is required"
        ) from exc


def point(raw):
    if not isinstance(raw, (tuple, list)) or len(raw) != 3:
        raise ContentPlanError("three exact spatial coordinates are required")
    return tuple(coordinate(v) for v in raw)


@dataclass(frozen=True)
class Cuboid:
    lower: tuple[sp.Rational, ...]
    upper: tuple[sp.Rational, ...]

    def __post_init__(self):
        lower, upper = point(self.lower), point(self.upper)
        if any(a >= b for a, b in zip(lower, upper)):
            raise ContentPlanError("a cuboid needs three positive edge lengths")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)

    @property
    def dimensions(self):
        return tuple(b - a for a, b in zip(self.lower, self.upper))

    @property
    def volume(self):
        return sp.prod(self.dimensions)

    @property
    def surface(self):
        x, y, z = self.dimensions
        return 2 * (x * y + x * z + y * z)


def _inside(box, p):
    return all(a <= v < b for a, b, v in zip(box.lower, box.upper, p))


def _grid(additions, cutouts):
    boxes = additions + cutouts
    axes = tuple(
        tuple(sorted({b.lower[i] for b in boxes} | {b.upper[i] for b in boxes}))
        for i in range(3)
    )
    if sp.prod(len(axis) - 1 for axis in axes) > 4096:
        raise ContentPlanError("the orthogonal diagram exceeds the reviewed cell bound")
    cells = set()
    for index in product(*(range(len(axis) - 1) for axis in axes)):
        p = tuple(axes[i][j] for i, j in enumerate(index))
        filled = any(_inside(b, p) for b in additions)
        removed = any(_inside(b, p) for b in cutouts)
        if removed and not filled:
            raise ContentPlanError("a cutout lies outside the original solid")
        if filled and not removed:
            cells.add(index)
    if not cells:
        raise ContentPlanError("a nonempty three-dimensional solid is required")
    return axes, frozenset(cells)


@dataclass(frozen=True)
class OrthogonalSolid:
    additions: tuple[Cuboid, ...]
    cutouts: tuple[Cuboid, ...] = ()
    axes: tuple[tuple[sp.Rational, ...], ...] = field(init=False, repr=False)
    cells: frozenset[tuple[int, ...]] = field(init=False, repr=False)

    def __post_init__(self):
        if (
            not isinstance(self.additions, tuple)
            or not isinstance(self.cutouts, tuple)
            or not self.additions
        ):
            raise ContentPlanError("explicit nonempty cuboid additions are required")
        if len(self.additions) + len(self.cutouts) > 24 or any(
            not isinstance(b, Cuboid) for b in self.additions + self.cutouts
        ):
            raise ContentPlanError("at most twenty-four reviewed cuboids are supported")
        axes, cells = _grid(self.additions, self.cutouts)
        object.__setattr__(self, "axes", axes)
        object.__setattr__(self, "cells", cells)

    def dimensions(self, index):
        return tuple(self.axes[i][j + 1] - self.axes[i][j] for i, j in enumerate(index))

    @property
    def volume(self):
        return sum(sp.prod(self.dimensions(cell)) for cell in self.cells)

    @property
    def directed_areas(self):
        areas = [sp.S.Zero] * 6
        for cell in self.cells:
            size = self.dimensions(cell)
            for axis, direction in product(range(3), (-1, 1)):
                neighbor = tuple(
                    v + (direction if i == axis else 0) for i, v in enumerate(cell)
                )
                if neighbor not in self.cells:
                    areas[2 * axis + (direction == 1)] += sp.prod(
                        size[i] for i in range(3) if i != axis
                    )
        return tuple(areas)

    @property
    def surface(self):
        return sum(self.directed_areas)

    def on_boundary(self, raw):
        p = point(raw)
        for cell in self.cells:
            for axis, direction in product(range(3), (-1, 1)):
                neighbor = tuple(
                    v + (direction if i == axis else 0) for i, v in enumerate(cell)
                )
                plane = self.axes[axis][cell[axis] + (direction == 1)]
                if (
                    neighbor not in self.cells
                    and p[axis] == plane
                    and all(
                        self.axes[i][cell[i]] <= p[i] <= self.axes[i][cell[i] + 1]
                        for i in range(3)
                        if i != axis
                    )
                ):
                    return True
        return False
