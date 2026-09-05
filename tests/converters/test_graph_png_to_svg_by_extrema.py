"""Regression tests for extrema-first raster graph curve fitting."""

from __future__ import annotations

import unittest

import numpy as np
from scipy.interpolate import PchipInterpolator

from solution_runner.converters import graph_png_to_svg_by_contrast as base
from solution_runner.converters import graph_png_to_svg_by_extrema as extrema_v2


class ExtremaDetectionTests(unittest.TestCase):
    """Verify stable extrema recovery independently from raster grid extraction."""

    @staticmethod
    def _four_extrema_trace() -> np.ndarray:
        """Return a quantized trace shaped like task 7091 in logical coordinates."""
        node_x = np.asarray([-1.0, 0.0, 2.0, 5.0, 7.0, 10.0])
        node_y = np.asarray([4.0, 2.28, 4.0, -4.0, 3.25, -3.72])
        x_values = np.linspace(-1.0, 10.0, 661)
        y_values = PchipInterpolator(node_x, node_y)(x_values)
        # Quantization deliberately creates short horizontal pixel shelves.
        y_values = np.round(y_values / 0.035) * 0.035
        return np.column_stack([x_values, y_values])

    def test_detects_and_snaps_four_expected_extrema(self) -> None:
        """Collapse quantized shelves into one correctly typed grid-aware extremum."""
        analysis, extrema = extrema_v2.detect_extrema(self._four_extrema_trace())

        self.assertEqual([item.kind for item in extrema], [
            "minimum",
            "maximum",
            "minimum",
            "maximum",
        ])
        np.testing.assert_allclose([item.x for item in extrema], [0.0, 2.0, 5.0, 7.0])
        self.assertTrue(all(item.snapped_x for item in extrema))
        self.assertEqual(analysis.shape, self._four_extrema_trace().shape)

    def test_ignores_subprominence_raster_wiggles(self) -> None:
        """Do not turn small contrast-trace jitter into mathematical extrema."""
        x_values = np.linspace(-2.0, 8.0, 601)
        y_values = 0.35 * x_values + 0.025 * np.sin(x_values * 18.0)
        trace = np.column_stack([x_values, y_values])

        _, extrema = extrema_v2.detect_extrema(
            trace,
            minimum_prominence_cells=0.18,
        )

        self.assertEqual(extrema, ())

    def test_preserves_near_endpoint_extremum_prominence(self) -> None:
        """Find a final peak instead of clipping it into an endpoint shelf."""
        node_x = np.asarray([0.0, 5.0, 9.6, 10.0])
        node_y = np.asarray([0.0, -2.0, 2.30, 2.0])
        x_values = np.linspace(0.0, 10.0, 701)
        trace = np.column_stack(
            [x_values, PchipInterpolator(node_x, node_y)(x_values)]
        )

        _, extrema = extrema_v2.detect_extrema(trace)

        final_maximum = [item for item in extrema if item.kind == "maximum"][-1]
        self.assertGreater(final_maximum.x, 9.35)
        self.assertLess(final_maximum.x, 9.85)

    def test_raw_grid_evidence_recovers_a_smoothing_shifted_minimum(self) -> None:
        """Snap a grid-node minimum when smoothing alone moved its apex inward."""
        x_values = np.linspace(1.0, 3.0, 401)
        smoothed_trace = np.column_stack(
            [x_values, 1.222 + np.square(x_values - 2.0)]
        )
        raw_grid_evidence = np.column_stack(
            [x_values, 1.098 + np.square(x_values - 2.0)]
        )

        _, without_evidence = extrema_v2.detect_extrema(
            smoothed_trace,
            analysis_smoothing_cells=0.0,
        )
        _, with_evidence = extrema_v2.detect_extrema(
            smoothed_trace,
            grid_evidence_trace=raw_grid_evidence,
            analysis_smoothing_cells=0.0,
        )

        self.assertEqual(len(without_evidence), 1)
        self.assertAlmostEqual(without_evidence[0].y, 1.222, places=3)
        self.assertFalse(without_evidence[0].snapped_y)
        self.assertEqual(len(with_evidence), 1)
        self.assertEqual((with_evidence[0].x, with_evidence[0].y), (2.0, 1.0))
        self.assertTrue(with_evidence[0].snapped_y)
        self.assertTrue(with_evidence[0].snapped_y_from_grid_evidence)

    def test_fit_has_one_horizontal_knot_per_extremum(self) -> None:
        """Round isolated extrema softly while preserving their support geometry."""
        analysis, extrema = extrema_v2.detect_extrema(self._four_extrema_trace())
        fit = extrema_v2.fit_logical_curve(
            analysis,
            extrema,
            maximum_error_cells=0.08,
            minimum_support_spacing_cells=0.18,
            extremum_shoulder_cells=0.50,
        )

        self.assertEqual(len(fit.extremum_knot_indices), 4)
        for index in fit.extremum_knot_indices:
            self.assertEqual(fit.slopes[index], 0.0)
            self.assertGreater(index, 0)
            self.assertLess(index, len(fit.logical_knots) - 1)
            left_distance = fit.logical_knots[index, 0] - fit.logical_knots[index - 1, 0]
            right_distance = fit.logical_knots[index + 1, 0] - fit.logical_knots[index, 0]
            self.assertLessEqual(left_distance, 0.51)
            self.assertLessEqual(right_distance, 0.51)
            self.assertGreaterEqual(
                abs(fit.logical_knots[index - 1, 1] - fit.logical_knots[index, 1]),
                0.119,
            )
            self.assertGreaterEqual(
                abs(fit.logical_knots[index + 1, 1] - fit.logical_knots[index, 1]),
                0.119,
            )

        baseline_slopes = extrema_v2._pchip_slopes_with_extrema(
            fit.logical_knots,
            fit.extremum_knot_indices,
            smoothing=fit.slope_smoothing,
            extremum_rounding=0.0,
        )

        def total_apex_curvature(slopes: np.ndarray) -> float:
            """Return summed one-sided curvature magnitudes at all extrema."""
            total = 0.0
            for index in fit.extremum_knot_indices:
                left_x, left_y = fit.logical_knots[index - 1]
                extremum_x, extremum_y = fit.logical_knots[index]
                right_x, right_y = fit.logical_knots[index + 1]
                left_width = extremum_x - left_x
                right_width = right_x - extremum_x
                left_curvature = (
                    6.0 * left_y
                    + 2.0 * left_width * slopes[index - 1]
                    - 6.0 * extremum_y
                ) / (left_width * left_width)
                right_curvature = (
                    -6.0 * extremum_y
                    + 6.0 * right_y
                    - 2.0 * right_width * slopes[index + 1]
                ) / (right_width * right_width)
                total += abs(left_curvature) + abs(right_curvature)
            return total

        self.assertLess(
            total_apex_curvature(fit.slopes),
            total_apex_curvature(baseline_slopes),
        )

        dense_x = np.linspace(fit.logical_knots[0, 0], fit.logical_knots[-1, 0], 3001)
        dense_y = extrema_v2._evaluate_hermite(fit.logical_knots, fit.slopes, dense_x)
        hard_x = [
            fit.logical_knots[0, 0],
            *[item.x for item in fit.extrema],
            fit.logical_knots[-1, 0],
        ]
        hard_y = [
            fit.logical_knots[0, 1],
            *[item.y for item in fit.extrema],
            fit.logical_knots[-1, 1],
        ]
        for left_x, right_x, left_y, right_y in zip(
            hard_x[:-1],
            hard_x[1:],
            hard_y[:-1],
            hard_y[1:],
        ):
            branch = dense_y[(dense_x >= left_x) & (dense_x <= right_x)]
            differences = np.diff(branch)
            if right_y > left_y:
                self.assertGreaterEqual(float(np.min(differences)), -1e-8)
            else:
                self.assertLessEqual(float(np.max(differences)), 1e-8)

    def test_endpoint_support_knots_skip_adjacent_ring_artifacts(self) -> None:
        """Keep endpoint handles away from near-vertical open-circle edges."""
        trace = np.asarray(
            [
                [0.00, 0.00],
                [0.02, 0.70],
                [0.20, 0.90],
                [0.50, 1.30],
                [1.00, 1.80],
                [1.50, 2.20],
                [1.80, 2.50],
                [1.98, 2.70],
                [2.00, 3.40],
            ],
            dtype=np.float64,
        )

        fit = extrema_v2.fit_logical_curve(
            trace,
            (),
            maximum_error_cells=10.0,
            minimum_support_spacing_cells=0.18,
            extremum_shoulder_cells=0.50,
        )

        self.assertGreaterEqual(
            fit.logical_knots[1, 0] - fit.logical_knots[0, 0],
            0.18 - 1e-9,
        )
        self.assertGreaterEqual(
            fit.logical_knots[-1, 0] - fit.logical_knots[-2, 0],
            0.18 - 1e-9,
        )

    def test_open_endpoint_centers_snap_to_grid(self) -> None:
        """Correct ring-edge tracing without changing the endpoint x-domain."""
        vertical = base.GridAxisModel((0.0, 10.0, 20.0), 0.0, 10.0, 0.0)
        horizontal = base.GridAxisModel((0.0, 10.0, 20.0), 0.0, 10.0, 0.0)
        grid = base.GridModel(
            vertical=vertical,
            horizontal=horizontal,
            vertical_axis_x=50.0,
            horizontal_axis_y=50.0,
            grid_mask_radius=1,
            detection_threshold=0.2,
            image_width=101,
            image_height=101,
        )
        points = np.asarray([[20.0, 10.0], [50.0, 50.0], [80.0, 87.3]])
        trace = base.TraceResult(
            raw_points=points.copy(),
            points=points.copy(),
            simplified_points=points.copy(),
            score=1.0,
            start=base.Endpoint(20.0, 10.0, -3.0, 4.0, True),
            end=base.Endpoint(80.0, 87.3, 3.0, -3.73, True),
        )

        corrected = extrema_v2.snap_open_endpoint_centers(trace, grid)

        self.assertEqual(corrected.start.logical_y, 4.0)
        self.assertEqual(corrected.end.logical_y, -4.0)
        self.assertEqual(corrected.start.logical_x, -3.0)
        self.assertEqual(corrected.end.logical_x, 3.0)
        self.assertEqual(corrected.points[0, 1], 10.0)
        self.assertEqual(corrected.points[-1, 1], 90.0)

    def test_axis_crossings_and_lattice_nodes_become_hard_knots(self) -> None:
        """Preserve OX/OY crossings and exact grid nodes during curve fitting."""
        x_values = np.linspace(-4.0, 4.0, 801)
        trace = np.column_stack([x_values, 0.5 * x_values])
        landmarks = extrema_v2.detect_landmarks(trace, ())

        landmark_coordinates = {(item.x, item.y) for item in landmarks}
        self.assertIn((0.0, 0.0), landmark_coordinates)
        self.assertIn((-2.0, -1.0), landmark_coordinates)
        self.assertIn((2.0, 1.0), landmark_coordinates)
        origin = next(item for item in landmarks if item.x == 0.0)
        self.assertIn("x_axis", origin.kinds)
        self.assertIn("y_axis", origin.kinds)
        self.assertIn("lattice", origin.kinds)

        fit = extrema_v2.fit_logical_curve(trace, (), landmarks)
        knot_coordinates = {
            (round(float(x), 8), round(float(y), 8))
            for x, y in fit.logical_knots
        }
        for landmark in fit.landmarks:
            self.assertIn(
                (round(landmark.x, 8), round(landmark.y, 8)),
                knot_coordinates,
            )

    def test_lattice_quantization_does_not_flatten_an_extremum(self) -> None:
        """Drop a same-level nearby lattice candidate that would form a shelf."""
        x_values = np.linspace(-1.0, 2.0, 601)
        trace = np.column_stack([x_values, 3.0 - (x_values - 0.65) ** 2])
        analysis, extrema = extrema_v2.detect_extrema(trace)

        landmarks = extrema_v2.detect_landmarks(analysis, extrema)

        self.assertEqual(len(extrema), 1)
        self.assertAlmostEqual(extrema[0].x, 0.65, places=2)
        self.assertNotIn((1.0, 3.0), {(item.x, item.y) for item in landmarks})


if __name__ == "__main__":
    unittest.main()
