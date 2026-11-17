"""Check the persisted diagnostic contract for polygon conversion."""

import numpy as np

from solution_runner.converters.polygon_diagnostics import (
    PolygonDiagnostics,
    write_polygon_diagnostics,
)


def test_polygon_diagnostics_preserve_geometry_and_dilation(tmp_path):
    axis = {
        "observed": [1, 3],
        "origin": 1,
        "step": 2,
        "max_residual": 0,
        "coverage": 1,
    }
    report = PolygonDiagnostics(
        out=tmp_path / "polygon.svg",
        src="source.png",
        dilation_results={0: [(1, 2)]},
        grayscale_source=True,
        w=4,
        h=3,
        base_mask=np.full((3, 4), 255, dtype=np.uint8),
        alpha_grid={"source": "grayscale", "x": axis, "y": axis},
        alpha_info={"alpha_shape_threshold": 128, "alpha_shape_bbox": (0, 0, 3, 2)},
        pad_cells=2,
        resolved_cell_size=20.0,
        template_svg=None,
        integer_quad=[(1, 2)],
        proto_info={
            "bbox": (0, 0, 3, 2),
            "source_quad_before_snap": [(1, 2)],
            "source_quad_on_alpha_grid": [(1, 2)],
            "grid_indices": [(1, 2)],
            "grid_bounds": (0, 0, 4, 3),
            "svg_size": (80, 60),
        },
        source_polygon_points=[(1, 2)],
    )
    write_polygon_diagnostics(report)
    text = report.out.with_suffix(".txt").read_text()
    assert "dilation_coordinates={0: [(1, 2)]}\n" in text
    assert "grayscale_dilation_coordinates={0: [(1, 2)]}\n" in text
    assert "size=4x3\nmask_pixels=12\ngrid_source=grayscale\n" in text
    assert text.endswith(
        "source_polygon_points=[(1, 2)]\ngrid_bounds=(0, 0, 4, 3)\nsvg_size=(80, 60)\n"
    )


def test_transparent_fill_counts_follow_source_line(tmp_path):

    # Build a minimal valid report while retaining the shared geometry serialization.
    axis = {"observed": [], "origin": 0, "step": 1, "max_residual": 0, "coverage": 1}
    report = PolygonDiagnostics(
        out=tmp_path / "fill.svg",
        src="fill.png",
        dilation_results=None,
        grayscale_source=False,
        w=1,
        h=1,
        base_mask=np.ones((1, 1), dtype=np.uint8),
        alpha_grid={"source": "alpha", "x": axis, "y": axis},
        alpha_info={"alpha_shape_threshold": 1, "alpha_shape_bbox": (0, 0, 0, 0)},
        pad_cells=0,
        resolved_cell_size=1.0,
        template_svg=None,
        integer_quad=[],
        proto_info={
            key: []
            for key in (
                "bbox",
                "source_quad_before_snap",
                "source_quad_on_alpha_grid",
                "grid_indices",
                "grid_bounds",
                "svg_size",
            )
        },
        source_polygon_points=[],
        preprocessing_info={
            "fill_pixels_replaced": 4,
            "embedded_grid_pixels_replaced": 2,
        },
    )
    write_polygon_diagnostics(report)
    assert (
        report.out.with_suffix(".txt")
        .read_text()
        .startswith(
            "source=fill.png\nfill_pixels_replaced=4\nembedded_grid_pixels_replaced=2\nsize=1x1\n"
        )
    )
