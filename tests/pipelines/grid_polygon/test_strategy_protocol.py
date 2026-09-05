"""Protect shared strategy rendering over validated legacy SVG geometry."""

from __future__ import annotations

from solution_runner.pipelines.grid_polygon.strategies.protocol import svg_coordinate_mapper


def test_mapper_accepts_a_validated_legacy_grid_with_small_interval_drift() -> None:
    """Render a snapped polygon when legacy grid intervals drift under one eighth cell."""

    logical = ((1, 4), (3, 1), (8, 10), (1, 5))
    actual = (
        (21.795, 59.215),
        (62.458, 0.779),
        (163.921, 182.065),
        (21.795, 79.82),
    )
    points = " ".join(f"{x},{y}" for x, y in actual)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 -19.267 184.824 222.066">'
        f'<polygon points="{points}" fill="#143B8F" stroke="#0D0F0F"/>'
        "</svg>"
    ).encode()

    mapper, cell_size = svg_coordinate_mapper(svg, logical)

    mapped = tuple(mapper(point) for point in logical)
    assert cell_size > 20
    assert all(
        max(abs(mx - ax), abs(my - ay)) <= cell_size * 0.12
        for (mx, my), (ax, ay) in zip(mapped, actual, strict=True)
    )
