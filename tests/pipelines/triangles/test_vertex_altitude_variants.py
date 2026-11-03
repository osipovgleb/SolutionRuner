"""Exercise all frames, exact special angles and the coincident-foot boundary."""

import itertools
from copy import deepcopy

import pytest
from test_two_ray_source_methods import replay
from test_vertex_altitude_preparation import check_rows, synthetic
from vertex_altitude_cases import plan, section

from solution_runner.pipelines.triangles.isosceles.vertex_altitude_figures import (
    selection,
)


@pytest.mark.parametrize("frame", list(itertools.permutations("ABC")))
@pytest.mark.parametrize("angle", [30, 45, 90, 120, 135])
@pytest.mark.parametrize("mode", ["side_angle", "height_angle"])
def test_forward_inverse_frames_topologies_and_coincident_foot(frame, angle, mode):
    case, ctx = synthetic(frame, angle, mode)
    before = deepcopy(ctx)
    m = selection(ctx)[0]
    result = plan(case, ctx)
    assert ctx == before
    replay(ctx, result.transformations)
    check_rows(section(ctx, "solution")["html"], m)
    assert plan(case, ctx).transformations == ()
    if angle == 90:
        assert "совпадает" in section(ctx, "solution")["html"]
        assert (
            r"\angle " + m.vertex + m.apex + "H" not in section(ctx, "solution")["html"]
        )


@pytest.mark.parametrize("frame", list(itertools.permutations("ABC")))
@pytest.mark.parametrize("angle", [30, 45, 60])
def test_three_inverse_angle_methods_adapt_only_valid_special_triangle_claims(
    frame, angle
):
    case, ctx = synthetic(frame, angle, "side_height")
    m = selection(ctx)[0]
    result = plan(case, ctx)
    assert result.answer == str(angle)
    replay(ctx, result.transformations)
    html = section(ctx, "solution")["html"]
    check_rows(html, m)
    assert plan(case, ctx).transformations == ()
