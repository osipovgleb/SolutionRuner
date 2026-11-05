"""Verify unions and exposed faces using native dimensions and independent unit voxels."""

from itertools import permutations, product
from math import lcm

import pytest
import sympy as sp

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.orthogonal_geometry import (
    Cuboid,
    OrthogonalSolid,
    coordinate,
)


def box(size, origin=(0, 0, 0)):
    origin = tuple(sp.Rational(n) for n in origin)
    return Cuboid(origin, tuple(x + sp.Rational(d) for x, d in zip(origin, size)))


# Dimensions transcribed from the fifteen parent diagrams, not from their answers.
PARENTS = [
    ("27044", (box((3, 1, 3)),), (box((1, 1, 1), (2, 0, 2)),), 8),
    ("27187", (box((5, 4, 4)),), (box((3, 4, 2), (2, 0, 2)),), 56),
    ("27188", (box((1, 4, 2)),), (box((1, 1, 1), (0, 0, 1)),), 7),
    ("27189", (box((4, 3, 4)),), (box((1, 2, 4), (3, 0, 0)),), 40),
    ("27190", (box((4, 3, 3)),), (box((2, 1, 1), (0, 0, 2)),), 34),
    ("27191", (box((5, 4, 2)),), (box((1, 2, 2), (2, 0, 0)),), 36),
    ("27192", (box((5, 4, 5)),), (box((5, 1, 2), (0, 0, 1)),), 90),
    ("27193", (box((4, 3, 1)), box((2, 3, 1), (1, 0, 1))), (), 18),
    ("27194", (box((1, 3, 4)), box((2, 3, 2), (1, 0, 1))), (), 24),
    ("27195", (box((6, 1, 8)),), (box((1, 1, 3), (2, 0, 2)),), 45),
    ("27210", (box((4, 5, 3)), box((3, 2, 3), (0, 3, 3))), (), 78),
    ("27211", (box((4, 3, 4)), box((2, 4, 7), (4, 0, 0))), (), 104),
    (
        "27212",
        (box((5, 3, 3)), box((5, 2, 3), (0, 1, 3)), box((2, 2, 3), (5, 1, 0))),
        (),
        87,
    ),
    (
        "27213",
        (box((5, 4, 3)), box((1, 3, 3), (-1, 1, 0)), box((5, 3, 3), (0, 1, 3))),
        (),
        114,
    ),
    ("27216", (box((4, 5, 4)),), (box((1, 2, 1), (3, 0, 3)),), 78),
]


SURFACES = dict(
    zip(
        (row[0] for row in PARENTS),
        (28, 100, 26, 76, 66, 80, 136, 48, 58, 126, 124, 156, 140, 154, 112),
    )
)


def voxel_measures(additions, cutouts):
    scale = lcm(*(int(x.q) for b in additions + cutouts for x in b.lower + b.upper))

    def units(boxes):
        result = set()
        for b in boxes:
            result.update(
                product(
                    *(
                        range(int(a * scale), int(z * scale))
                        for a, z in zip(b.lower, b.upper)
                    )
                )
            )
        return result

    occupied = units(additions) - units(cutouts)
    faces = sum(
        tuple(v + (d if j == axis else 0) for j, v in enumerate(cell)) not in occupied
        for cell in occupied
        for axis, d in product(range(3), (-1, 1))
    )
    return sp.Rational(len(occupied), scale**3), sp.Rational(faces, scale**2)


@pytest.mark.parametrize(
    "group,additions,cutouts,answer", PARENTS, ids=[r[0] for r in PARENTS]
)
def test_native_volume_and_independent_exposed_faces(group, additions, cutouts, answer):
    solid = OrthogonalSolid(additions, cutouts)
    volume, surface = voxel_measures(additions, cutouts)
    assert solid.volume == answer == volume
    assert solid.surface == surface == SURFACES[group]
    assert all(
        solid.directed_areas[2 * i] == solid.directed_areas[2 * i + 1] for i in range(3)
    )


@pytest.mark.parametrize("order", list(permutations(range(3))))
def test_axis_permutation_translation_and_fractional_cell_size(order):
    additions = (box((3, 2, 4)), box((2, 1, 2), (2, 1, 3)))
    cutouts = (box((1, 1, 2), (0, 0, 1)),)
    initial = OrthogonalSolid(additions, cutouts)

    def change(b):
        return Cuboid(
            tuple(b.lower[i] / 2 - 3 for i in order),
            tuple(b.upper[i] / 2 - 3 for i in order),
        )

    adds, cuts = tuple(map(change, additions)), tuple(map(change, cutouts))
    changed = OrthogonalSolid(adds, cuts)
    volume, surface = voxel_measures(adds, cuts)
    assert changed.volume == volume == initial.volume / 8
    assert changed.surface == surface == initial.surface / 4


def test_partition_and_overlapping_additions_do_not_count_internal_faces():
    original = OrthogonalSolid((box((5, 3, 2)),))
    split = OrthogonalSolid(
        (
            box((sp.Rational(3, 2), 3, 2)),
            box((sp.Rational(7, 2), 3, 2), (sp.Rational(3, 2), 0, 0)),
        )
    )
    overlap = OrthogonalSolid((box((4, 3, 2)), box((3, 3, 2), (2, 0, 0))))
    duplicate = OrthogonalSolid((box((5, 3, 2)), box((5, 3, 2))))
    for solid in (split, overlap, duplicate):
        assert solid.volume == original.volume and solid.surface == original.surface
        assert not solid.on_boundary((sp.Rational(3, 2), 1, 1))


def test_intersecting_through_holes_remove_shared_material_once():
    adds = (box((5, 5, 5)),)
    cuts = (box((1, 5, 1), (2, 0, 2)), box((5, 1, 1), (0, 2, 2)))
    solid = OrthogonalSolid(adds, cuts)
    volume, surface = voxel_measures(adds, cuts)
    assert solid.volume == volume == 116
    assert solid.surface == surface


@pytest.mark.parametrize("offset", [sp.Rational(1, 2), 1, sp.Rational(3, 2), 2])
def test_unlabelled_slot_height_changes_no_volume_or_surface(offset):
    solid = OrthogonalSolid((box((5, 4, 5)),), (box((5, 1, 2), (0, 0, offset)),))
    assert solid.volume == 90 and solid.surface == 136


@pytest.mark.parametrize("x,z", [(1, 1), (2, 2), (3, 4)])
def test_internal_through_hole_position_does_not_change_measures(x, z):
    solid = OrthogonalSolid((box((6, 1, 8)),), (box((1, 1, 3), (x, 0, z)),))
    assert solid.volume == 45 and solid.surface == 126


def test_hole_walls_and_openings_are_distinguished_from_material_boundary():
    solid = OrthogonalSolid((box((5, 1, 5)),), (box((1, 1, 1), (2, 0, 2)),))
    assert solid.on_boundary((2, sp.Rational(1, 2), sp.Rational(5, 2)))
    assert solid.on_boundary((0, 0, 0))
    assert not solid.on_boundary((sp.Rational(5, 2), 0, sp.Rational(5, 2)))
    assert not solid.on_boundary((1, sp.Rational(1, 2), 1))
    assert not solid.on_boundary((10, 0, 0))


@pytest.mark.parametrize(
    "raw",
    [
        True,
        0.1,
        float("inf"),
        sp.sqrt(2),
        "nan",
        "1/0",
        "1000000001",
        "__import__('os')",
    ],
)
def test_coordinates_are_bounded_exact_numbers(raw):
    with pytest.raises(ContentPlanError):
        coordinate(raw)


@pytest.mark.parametrize(
    "lower,upper", [((0, 0), (1, 1, 1)), ((0, 0, 0), (1, 0, 1)), ((1, 0, 0), (0, 1, 1))]
)
def test_degenerate_or_malformed_cuboids_are_rejected(lower, upper):
    with pytest.raises(ContentPlanError):
        Cuboid(lower, upper)


@pytest.mark.parametrize(
    "additions,cutouts",
    [
        ((), ()),
        ((box((1, 1, 1)),), (box((1, 1, 1)),)),
        ((box((1, 1, 1)),), (box((1, 1, 1), (1, 0, 0)),)),
        ((box((1, 1, 1)), box((1, 1, 1), (2, 0, 0))), (box((2, 1, 1)),)),
        ((box((1, 1, 1)),) * 25, ()),
        (tuple(box((1, 1, 1), (2 * i, 2 * i, 2 * i)) for i in range(24)), ()),
    ],
)
def test_empty_outside_or_excessively_large_grids_fail_closed(additions, cutouts):
    with pytest.raises(ContentPlanError):
        OrthogonalSolid(additions, cutouts)


@pytest.mark.parametrize("offset", [0, sp.Rational(1, 2), 1, sp.Rational(3, 2), 2])
def test_unlabelled_top_bar_and_side_shelf_placements_preserve_measures(offset):
    bar = OrthogonalSolid((box((4, 3, 1)), box((2, 3, 1), (offset, 0, 1))))
    shelf = OrthogonalSolid((box((1, 3, 4)), box((2, 3, 2), (1, 0, offset))))
    assert bar.volume == 18 and bar.surface == 48
    assert shelf.volume == 24 and shelf.surface == 58


@pytest.mark.parametrize(
    "x,y", [(0, 0), (1, 3), (sp.Rational(1, 2), sp.Rational(3, 2))]
)
def test_top_block_location_inside_its_base_does_not_change_measures(x, y):
    solid = OrthogonalSolid((box((4, 5, 3)), box((3, 2, 3), (x, y, 3))))
    assert solid.volume == 78 and solid.surface == 124


def test_three_surface_sum_in_parent_77157_requires_hidden_central_block_cancellation():
    adds = (box((6, 3, 2)), box((6, 2, 4), (0, 1, 2)), box((2, 2, 2), (-2, 1, 0)))
    solid = OrthogonalSolid(adds)
    volume, surface = voxel_measures(adds, ())
    assert solid.volume == volume == 92 and solid.surface == surface == 152
    central = box((6, 2, 2))
    assert central.surface == 2 * (6 * 2 + 6 * 2 + 2 * 2)
    upper, front, side = box((6, 2, 4)), box((6, 1, 2)), box((2, 2, 2))
    assert solid.surface == upper.surface + front.surface + side.surface
    assert solid.volume != upper.volume + front.volume + side.volume


def test_equal_volume_does_not_prove_the_same_geometric_region():
    whole = OrthogonalSolid((box((4, 3, 2)),))
    split = OrthogonalSolid((box((1, 3, 2)), box((3, 3, 2), (1, 0, 0))))
    other = OrthogonalSolid((box((4, 3, 2), (1, 0, 0)),))
    assert whole.equivalent(split) and split.equivalent(whole)
    assert whole.volume == other.volume and whole.surface == other.surface
    assert not whole.equivalent(other)
