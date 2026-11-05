"""Check unseen dimensions, topology restrictions and spatial partition witnesses."""

import pytest

from solution_runner.pipelines.core.errors import ContentPlanError
from solution_runner.pipelines.solids.orthogonal_shapes import assembled, block, build


@pytest.mark.parametrize(
    "kind,given,expected",
    [
        ("step_width", (7, 2, 5, 3, 2), 62),
        ("step_rise", (7, 2, 5, 2, 3), 54),
        ("depth_step", (3, 7, 6, 2, 3), 108),
        ("plan_step", (6, 5, 2, 2, 3), 48),
        ("upper_corner_left", (5, 4, 6, 2, 1, 3), 114),
        ("front_notch", (7, 4, 3, 3, 2), 66),
        ("front_groove", (7, 4, 6, 1, 2), 154),
        ("bar", (7, 3, 2, 3, 4), 78),
        ("shelf", (2, 3, 7, 4, 3), 78),
        ("through_plate", (7, 2, 9, 3, 4), 102),
        ("pedestal", (6, 7, 8, 4, 3, 3), 246),
        ("side_boxes", (8, 5, 3, 2, 4, 6), 102),
        ("right_wing", (9, 6, 4, 2, 7, 3), 156),
        ("left_wing", (9, 7, 4, 2, 7, 3), 170),
        ("upper_corner_right", (5, 4, 6, 2, 1, 3), 114),
    ],
)
def test_unseen_dimensions_use_geometric_regions(kind, given, expected):
    assert build(kind, given).answer == expected


@pytest.mark.parametrize(
    "kind,given",
    [
        ("step_width", (4, 3, 2, 3, 1)),
        ("step_rise", (4, 3, 2, 1, 4)),
        ("depth_step", (4, 3, 2, 1, 3)),
        ("plan_step", (4, 3, 2, 4, 1)),
        ("upper_corner_left", (4, 3, 2, 4, 1, 1)),
        ("front_notch", (4, 3, 2, 4, 1)),
        ("front_groove", (4, 3, 2, 1, 2)),
        ("bar", (4, 3, 2, 4, 1)),
        ("shelf", (4, 3, 2, 1, 2)),
        ("through_plate", (4, 3, 2, 1, 2)),
        ("pedestal", (4, 3, 2, 4, 1, 1)),
        ("side_boxes", (4, 3, 3, 2, 2, 3)),
        ("right_wing", (4, 3, 3, 3, 2, 1)),
        ("left_wing", (4, 4, 3, 2, 2, 1)),
        ("upper_corner_right", (4, 3, 2, 1, 1, 2)),
        ("bar", (4, 3, 0, 1, 1)),
        ("bar", (4, 3, -1, 1, 1)),
        ("bar", (4, 3, 2, 1)),
        ("foreign", (4, 3, 2, 1, 1)),
    ],
)
def test_impossible_or_incomplete_topologies_fail_closed(kind, given):
    with pytest.raises(ContentPlanError):
        build(kind, given)


def test_equal_volume_and_duplicate_parts_do_not_prove_a_partition():
    body = (block((2, 2, 2)),)
    shifted = (block((1, 2, 2), (1, 0, 0)), block((1, 2, 2), (2, 0, 0)))
    overlapping = (block((2, 2, 2)), block((1, 1, 1)))
    for parts in (shifted, overlapping):
        with pytest.raises(ContentPlanError):
            assembled(body, parts=parts)
