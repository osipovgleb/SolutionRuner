"""Template selection keeps the usable fill and outline inside the SVG canvas."""

from solution_runner.converters.polygon_svg_template import _extract_template_layers


def test_template_selects_in_canvas_fill_and_largest_outline(tmp_path):
    template = tmp_path / "template.svg"
    template.write_text(
        '<svg viewBox="0 0 10 10">'
        '<line x1="2" y1="0" x2="2" y2="10"/>'
        '<line x1="0" y1="3" x2="10" y2="3"/>'
        '<polygon points="-10,-10 20,-10 20,20" fill="red"/>'
        '<polygon points="1,1 8,1 8,8" fill="blue"/>'
        '<polygon points="1,1 8,1 8,8" fill="none" stroke="black"/>'
        "</svg>",
        encoding="utf-8",
    )
    layers = _extract_template_layers(template)
    assert (layers["vb_w"], layers["vb_h"]) == (10, 10)
    assert 'fill="blue"' in layers["fill_polygon"]
    assert 'stroke="black"' in layers["outline_polygon"]
    assert layers["grid_x"] == [2.0]
    assert layers["grid_y"] == [3.0]
