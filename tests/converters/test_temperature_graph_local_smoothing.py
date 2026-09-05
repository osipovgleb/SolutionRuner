"""Regression tests for bounded local temperature-curve smoothing."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import importlib
import unittest

import numpy as np

from solution_runner.converters.temperature_graph_png_to_svg import TemperatureGraphAnalysis


class TemperatureGraphLocalSmoothingTests(unittest.TestCase):
    """Protect the verified trace while removing only pixel-scale jitter."""

    @staticmethod
    def _analysis() -> TemperatureGraphAnalysis:
        """Return a hand-checked curve whose requested maximum is −10 °C."""

        xs = np.arange(0.0, 121.0)
        base = 30.0 + 8.0 * np.cos((xs - 20.0) * np.pi / 20.0)
        jitter = np.where((xs.astype(int) % 2) == 0, 0.3, -0.3)
        return TemperatureGraphAnalysis(
            plot_left=0.0,
            plot_top=0.0,
            plot_right=120.0,
            plot_bottom=60.0,
            x_grid_step=10.0,
            y_grid_step=10.0,
            horizontal_grid_count=7,
            vertical_grid_count=13,
            degrees_per_pixel=-0.5,
            temperature_intercept=1.0,
            day_labels=(date(2000, 1, 22), date(2000, 1, 23), date(2000, 1, 24)),
            requested_day_index=0,
            maximum_temperature=-10,
            curve_points=tuple((float(x), float(y)) for x, y in zip(xs, base + jitter)),
            chromatic_curve=True,
        )

    def test_removes_pixel_jitter_without_moving_endpoints_or_answer(self) -> None:
        """Fail if local smoothing redraws geometry or changes the verified result."""

        try:
            handler = importlib.import_module("solution_runner.converters.temperature_graph_local_smoothing")
        except ModuleNotFoundError:
            self.fail("temperature_graph_local_smoothing handler is missing")
        source = self._analysis()

        result = handler.smooth_temperature_curve(source)
        before = np.asarray(source.curve_points)
        after = np.asarray(result.analysis.curve_points)

        self.assertEqual(result.maximum_temperature, -10)
        self.assertLessEqual(result.maximum_deviation_cells, 0.05)
        np.testing.assert_array_equal(after[:, 0], before[:, 0])
        np.testing.assert_array_equal(after[[0, -1], 1], before[[0, -1], 1])
        self.assertLess(np.std(np.diff(after[:, 1], 2)), np.std(np.diff(before[:, 1], 2)) * 0.5)

    def test_rejects_material_local_redrawing(self) -> None:
        """Fail if a large isolated displacement can pass as pixel smoothing."""

        try:
            handler = importlib.import_module("solution_runner.converters.temperature_graph_local_smoothing")
        except ModuleNotFoundError:
            self.fail("temperature_graph_local_smoothing handler is missing")
        source = self._analysis()
        points = list(source.curve_points)
        points[50] = (points[50][0], points[50][1] + 5.0)
        displaced = replace(source, curve_points=tuple(points))

        with self.assertRaisesRegex(ValueError, "exceeds 0.050 grid cells"):
            handler.smooth_temperature_curve(displaced)


if __name__ == "__main__":
    unittest.main()
