"""Protect axis-aligned triangle analysis and independent area agreement."""

from __future__ import annotations

from fractions import Fraction

import pytest

from solution_runner.pipelines.grid_polygon.geometry.triangle import (
    GeometryMismatchError,
    analyze_axis_aligned_triangle,
    analyze_right_triangle,
    verify_triangle_area,
)


def test_axis_aligned_triangle_detects_vertical_base_and_horizontal_height() -> None:
    """Catch assuming every triangle base is horizontal."""

    analysis = analyze_axis_aligned_triangle(((2, 2), (1, 7), (2, 11)))

    assert analysis.base_start == (2, 2)
    assert analysis.base_end == (2, 11)
    assert analysis.apex == (1, 7)
    assert analysis.altitude_foot == (2, 7)
    assert analysis.base_length == 9
    assert analysis.height == 1
    assert analysis.area == Fraction(9, 2)
    assert analysis.area_by_coordinates == Fraction(9, 2)


def test_right_triangle_requires_axis_aligned_catheti() -> None:
    """Catch accepting a generic triangle in the right-triangle strategy."""

    analysis = analyze_right_triangle(((1, 2), (7, 2), (1, 6)))
    assert analysis.cathetus_lengths == (6, 4)
    assert analysis.area == Fraction(12)
    with pytest.raises(ValueError, match="right angle"):
        analyze_right_triangle(((1, 1), (4, 2), (2, 5)))


def test_triangle_area_mismatch_stops_answer_generation() -> None:
    """Catch trusting a decomposition value that disagrees with coordinates."""

    with pytest.raises(GeometryMismatchError, match="disagree"):
        verify_triangle_area(((1, 2), (7, 2), (1, 6)), Fraction(13))
