"""Regression tests for shape-preserving temperature-curve smoothing."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
import importlib
import unittest

import numpy as np

from solution_runner.converters.temperature_graph_png_to_svg import TemperatureGraphAnalysis


class TemperatureGraphPchipTests(unittest.TestCase):
    """Protect extrema and bounded geometry while removing pixel jitter."""

    @staticmethod
    def _analysis(*, noisy: bool = True) -> TemperatureGraphAnalysis:
        """Return a hand-checked three-day trace with one peak at −10 °C."""

        xs = np.arange(0.0, 121.0)
        base = 30.0 + 8.0 * np.cos((xs - 20.0) * np.pi / 20.0)
        jitter = np.where((xs.astype(int) % 2) == 0, 0.45, -0.45) if noisy else 0.0
        points = tuple((float(x), float(y)) for x, y in zip(xs, base + jitter))
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
            curve_points=points,
            chromatic_curve=True,
        )

    def test_smooths_pixel_jitter_without_changing_verified_daily_maximum(self) -> None:
        """Fail if smoothing preserves jitter or invents a different answer."""

        try:
            handler = importlib.import_module("solution_runner.converters.temperature_graph_pchip")
        except ModuleNotFoundError:
            self.fail("temperature_graph_pchip handler is missing")

        source = self._analysis()
        result = handler.smooth_temperature_curve(source)
        source_y = np.asarray([point[1] for point in source.curve_points])
        smooth_y = np.asarray([point[1] for point in result.analysis.curve_points])

        self.assertEqual(result.maximum_temperature, -10)
        self.assertLess(np.std(np.diff(smooth_y, 2)), np.std(np.diff(source_y, 2)) * 0.25)
        self.assertLessEqual(result.maximum_deviation_cells, 0.15)
        self.assertEqual(len(result.analysis.curve_points), len(source.curve_points))

    def test_rejects_a_curve_that_requires_more_than_bounded_displacement(self) -> None:
        """Fail if PCHIP can silently redraw materially different geometry."""

        try:
            handler = importlib.import_module("solution_runner.converters.temperature_graph_pchip")
        except ModuleNotFoundError:
            self.fail("temperature_graph_pchip handler is missing")

        source = self._analysis(noisy=False)
        displaced = replace(
            source,
            curve_points=tuple(
                (x, y + (4.0 if index % 2 else -4.0))
                for index, (x, y) in enumerate(source.curve_points)
            ),
        )

        with self.assertRaisesRegex(ValueError, "exceeds 0.150 grid cells"):
            handler.smooth_temperature_curve(displaced)

    def test_keeps_a_steep_curve_inside_the_same_bounded_geometry(self) -> None:
        """Fail if sparse anchors displace a legitimate steep curve near its edge."""

        handler = importlib.import_module("solution_runner.converters.temperature_graph_pchip")
        source = self._analysis(noisy=False)
        xs = np.arange(0.0, 121.0)
        jitter = np.where((xs.astype(int) % 2) == 0, 0.45, -0.45)
        ys = 30.0 + 8.0 * np.sin(xs * 2.0 * np.pi / 24.0) + jitter
        steep = replace(
            source,
            curve_points=tuple((float(x), float(y)) for x, y in zip(xs, ys)),
        )

        result = handler.smooth_temperature_curve(steep)

        self.assertEqual(result.maximum_temperature, -10)
        self.assertLessEqual(result.maximum_deviation_cells, 0.15)


if __name__ == "__main__":
    unittest.main()
