"""Regression tests for calendar temperature-graph vectorization."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path
import re
import tempfile
import unittest

import cv2
import numpy as np

from solution_runner.converters import temperature_graph_png_to_svg as subject


class TemperatureGraphVectorizerTests(unittest.TestCase):
    """Protect unequal-axis grid recovery, extrema, and vector-only output."""

    @staticmethod
    def _calendar_graph() -> np.ndarray:
        """Return a three-day graph with 6-hour columns and half-degree rows."""

        image = np.full((247, 397, 4), 255, dtype=np.uint8)
        left, top, right, bottom = 38, 13, 374, 202
        for x in range(left, right + 1, 28):
            color = (80, 80, 80, 255) if (x - left) % 112 == 0 else (196, 196, 196, 255)
            cv2.line(image, (x, top), (x, bottom), color, 1)
        for y in range(top, bottom + 1, 10):
            color = (138, 138, 138, 255) if (y - top) % 20 == 0 else (210, 210, 210, 255)
            cv2.line(image, (left, y), (right, y), color, 1)

        knots = np.asarray(
            [
                [38, 118],
                [94, 34],
                [150, 139],
                [206, 97],
                [262, 139],
                [318, 55],
                [374, 118],
            ],
            dtype=np.float32,
        )
        curve = []
        for x in range(left, right + 1):
            y = float(np.interp(x, knots[:, 0], knots[:, 1]))
            curve.append((x, round(y)))
        cv2.polylines(image, [np.asarray(curve, dtype=np.int32)], False, (31, 31, 31, 255), 2)
        return image

    def test_vectorizes_nonsquare_calendar_grid_and_verifies_requested_maximum(self) -> None:
        """Fail if a calendar graph is forced through square-grid geometry."""

        analysis = subject.analyze_temperature_graph(
            self._calendar_graph(),
            y_axis_labels=((13.0, 2.0), (55.0, 0.0), (97.0, -2.0)),
            day_labels=(date(2026, 12, 18), date(2026, 12, 19), date(2026, 12, 20)),
            requested_date=date(2026, 12, 19),
        )

        self.assertEqual(analysis.maximum_temperature, -2)
        self.assertEqual(analysis.requested_day_index, 1)
        self.assertAlmostEqual(analysis.x_grid_step, 28.0, delta=0.6)
        self.assertAlmostEqual(analysis.y_grid_step, 10.0, delta=0.6)
        self.assertAlmostEqual(analysis.degrees_per_pixel, -1 / 21, places=3)

        svg = subject.render_temperature_graph_svg(analysis)
        self.assertIn("19 декабря", svg)
        self.assertIn("<path", svg)
        self.assertNotIn("<image", svg)
        self.assertNotIn("<style", svg)
        self.assertNotRegex(svg, r">-?\d+\.\d{2,}<")
        dense_points = tuple(
            (analysis.plot_left + index, analysis.plot_top + index % 7)
            for index in range(500)
        )
        dense_svg = subject.render_temperature_graph_svg(
            replace(analysis, curve_points=dense_points)
        )
        curve_path = re.search(r'<path d="([^"]+)"', dense_svg)
        self.assertIsNotNone(curve_path)
        self.assertNotIn(" L", curve_path.group(1))
        self.assertEqual(curve_path.group(1).count(" C"), len(dense_points) - 1)

    def test_recovers_half_degree_scale_when_ocr_drops_minus_signs(self) -> None:
        """Fail if OCR punctuation is trusted instead of the monotone tick sequence."""

        lines = tuple(14.0 + 10.5 * index for index in range(20))
        tokens = (
            "2", "", "1", "", "0", "", "1", "", "-2", "", "3", "", "-4",
            "", "5", "", "-6", "", "7", "",
        )

        labels = subject.recover_y_axis_labels(lines, tokens)

        self.assertEqual(labels[0], (14.0, 2.0))
        self.assertEqual(labels[4], (56.0, 0.0))
        self.assertEqual(labels[8], (98.0, -2.0))

    def test_parses_requested_date_and_three_ocr_dates(self) -> None:
        """Fail if soft hyphens or Russian month labels break day selection."""

        requested = subject.requested_date_from_condition(
            "Определите наибольшую температуру 19 де­каб­ря."
        )
        days = subject.day_labels_from_ocr(
            "18 декабря\n19 декабря\n20 декабря",
            requested,
        )

        self.assertEqual(requested, date(2000, 12, 19))
        self.assertEqual(days, (date(2000, 12, 18), date(2000, 12, 19), date(2000, 12, 20)))

    def test_converter_writes_verified_svg_and_diagnostics(self) -> None:
        """Fail if a mismatched answer can produce an uploadable SVG artifact."""

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "task-5349.png"
            cv2.imwrite(str(source), cv2.cvtColor(self._calendar_graph(), cv2.COLOR_RGBA2BGRA))

            result = subject.convert_temperature_graph(
                source,
                root / "out",
                condition_text="Определите наибольшую температуру 19 декабря.",
                expected_answer=-2,
                ocr_reader=lambda _image, lines, _output: (
                    tuple("2" if i == 0 else "1" if i == 2 else "0" if i == 4 else "" for i in range(len(lines))),
                    "18 декабря 19 декабря 20 декабря",
                ),
            )

            self.assertTrue(result.svg_path.is_file())
            self.assertTrue(result.diagnostics_path.is_file())
            self.assertEqual(result.analysis.maximum_temperature, -2)

            with self.assertRaisesRegex(ValueError, "does not match expected answer"):
                subject.convert_temperature_graph(
                    source,
                    root / "wrong",
                    condition_text="19 декабря",
                    expected_answer=99,
                    ocr_reader=lambda _image, lines, _output: (
                        tuple("2" if i == 0 else "1" if i == 2 else "0" if i == 4 else "" for i in range(len(lines))),
                        "18 декабря 19 декабря 20 декабря",
                    ),
                )


if __name__ == "__main__":
    unittest.main()
