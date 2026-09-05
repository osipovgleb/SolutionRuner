"""Regression tests for deterministic raster-annulus SVG rendering."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree

from solution_runner.converters.png_to_svg_ring_by_contrast import _integer_circle_points, _ring_svg


class RingSvgCanvasTests(unittest.TestCase):
    """Protect the rendered circle from clipping at the SVG viewport."""

    def test_canvas_contains_outer_circle_for_diagonal_lattice_radius(self) -> None:
        """Size the canvas from the true radius, not integer point extrema."""

        center = (5, 5)
        outer_radius_squared = 18
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "ring.svg"
            _ring_svg(
                output,
                center,
                outer_radius_squared,
                17,
                _integer_circle_points(center, outer_radius_squared),
                1,
                20.0,
                True,
                True,
            )
            root = ElementTree.fromstring(output.read_bytes())

        _, _, width, height = map(float, root.attrib["viewBox"].split())
        circles = [element for element in root.iter() if element.tag.endswith("circle")]
        outer = max(circles, key=lambda element: float(element.attrib["r"]))
        cx = float(outer.attrib["cx"])
        cy = float(outer.attrib["cy"])
        radius = float(outer.attrib["r"])

        self.assertGreaterEqual(cx - radius, 0.0)
        self.assertLessEqual(cx + radius, width)
        self.assertGreaterEqual(cy - radius, 0.0)
        self.assertLessEqual(cy + radius, height)
        lines = [element for element in root.iter() if element.tag.endswith("line")]
        vertical_grid_x = {
            float(element.attrib["x1"])
            for element in lines
            if element.attrib.get("x1") == element.attrib.get("x2")
        }
        horizontal_grid_y = {
            float(element.attrib["y1"])
            for element in lines
            if element.attrib.get("y1") == element.attrib.get("y2")
        }
        self.assertEqual(max(vertical_grid_x), width)
        self.assertEqual(max(horizontal_grid_y), height)


if __name__ == "__main__":
    unittest.main()
