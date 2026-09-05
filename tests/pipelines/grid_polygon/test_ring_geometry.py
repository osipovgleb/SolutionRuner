"""Protect ring SVG parsing for converter output and legacy source assets."""

from __future__ import annotations

import pytest

from solution_runner.pipelines.grid_polygon.geometry.ring import RingGeometryError, parse_ring_svg


def test_parse_converter_ring_svg_uses_grid_and_circle_geometry() -> None:
    """Recover exact lattice radii from canonical circle elements."""

    svg = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 220">
      <g id="grid">
        <line x1="0" y1="0" x2="0" y2="220"/>
        <line x1="20" y1="0" x2="20" y2="220"/>
        <line x1="0" y1="0" x2="220" y2="0"/>
        <line x1="0" y1="20" x2="220" y2="20"/>
      </g>
      <g id="ring-outline">
        <circle cx="100" cy="100" r="84.852814"/>
        <circle cx="100" cy="100" r="82.462113"/>
      </g>
    </svg>'''

    geometry = parse_ring_svg(svg)

    assert geometry.center == (5, 5)
    assert geometry.outer_radius_squared == 18
    assert geometry.inner_radius_squared == 17


def test_parse_ring_svg_rejects_outer_circle_clipped_by_viewbox() -> None:
    """Fail closed before a visibly clipped converter artifact can be uploaded."""

    svg = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 160 180">
      <g id="grid">
        <line x1="0" y1="0" x2="0" y2="180"/>
        <line x1="20" y1="0" x2="20" y2="180"/>
        <line x1="0" y1="0" x2="160" y2="0"/>
        <line x1="0" y1="20" x2="160" y2="20"/>
      </g>
      <g id="ring-outline">
        <circle cx="80" cy="80" r="84.852814"/>
        <circle cx="80" cy="80" r="82.462113"/>
      </g>
    </svg>'''

    with pytest.raises(RingGeometryError, match="outside its viewBox"):
        parse_ring_svg(svg)


def test_parse_legacy_ring_svg_uses_circle_like_paths() -> None:
    """Handle saved SVGs whose circles are encoded as relative cubic paths."""

    svg = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 164 164">
      <line x1="0" y1="0" x2="164" y2="0"/>
      <line x1="0" y1="20.5" x2="164" y2="20.5"/>
      <line x1="0" y1="0" x2="0" y2="164"/>
      <line x1="20.5" y1="0" x2="20.5" y2="164"/>
      <path fill="#aaa" d="M82,17.5c-35,0-64.5,29-64.5,64.5c0,35.5 29,64.5 64.5,64.5z"/>
      <path fill="none" stroke="#111" d="M82,17.5c-35,0-64.5,29-64.5,64.5c0,35.5 29,64.5 64.5,64.5z"/>
      <path fill="#fff" d="M82,41c-22,0-41,18-41,41c0,23 19,41 41,41z"/>
    </svg>'''

    geometry = parse_ring_svg(svg)

    assert geometry.outer_radius_squared == 10
    assert geometry.inner_radius_squared == 4


def test_parse_ring_svg_detects_offset_nested_circles_per_task() -> None:
    """Catch rejection or forced concentric treatment of a valid shifted ring."""

    svg = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 220">
      <line x1="0" y1="0" x2="220" y2="0"/>
      <line x1="0" y1="20" x2="220" y2="20"/>
      <line x1="0" y1="0" x2="0" y2="220"/>
      <line x1="20" y1="0" x2="20" y2="220"/>
      <circle cx="100" cy="100" r="80"/>
      <circle cx="120" cy="100" r="40"/>
    </svg>'''

    geometry = parse_ring_svg(svg)

    assert geometry.alignment == "offset"
    assert geometry.center == (5, 5)
    assert geometry.inner_center == (6, 5)
    assert geometry.outer_radius_squared == 16
    assert geometry.inner_radius_squared == 4


def test_parse_ring_svg_rejects_non_nested_offset_circles() -> None:
    """Catch treating two intersecting circles as a shaded nested ring."""

    svg = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 220">
      <line x1="0" y1="0" x2="240" y2="0"/>
      <line x1="0" y1="20" x2="240" y2="20"/>
      <line x1="0" y1="0" x2="0" y2="220"/>
      <line x1="20" y1="0" x2="20" y2="220"/>
      <circle cx="100" cy="100" r="80"/>
      <circle cx="160" cy="100" r="40"/>
    </svg>'''

    with pytest.raises(RingGeometryError, match="not nested"):
        parse_ring_svg(svg)


def test_parse_ring_svg_recovers_both_circles_from_one_compound_path() -> None:
    """Catch loss of the inner circle when one legacy path has two subpaths."""

    svg = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 220">
      <line x1="0" y1="0" x2="220" y2="0"/>
      <line x1="0" y1="20" x2="220" y2="20"/>
      <line x1="0" y1="0" x2="0" y2="220"/>
      <line x1="20" y1="0" x2="20" y2="220"/>
      <path d="M100,20 c-40,0 -80,40 -80,80 c0,40 40,80 80,80z
               M120,60 c-20,0 -40,20 -40,40 c0,20 20,40 40,40z"/>
    </svg>'''

    geometry = parse_ring_svg(svg)

    assert geometry.alignment == "offset"
    assert geometry.outer_radius_squared == 16
    assert geometry.inner_radius_squared == 4


def test_parse_ring_svg_prefers_outline_paths_over_layered_fill_copies() -> None:
    """Do not mistake a second anti-aliasing fill layer for the inner circle."""

    svg = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 220">
      <line x1="0" y1="0" x2="220" y2="0"/>
      <line x1="0" y1="20" x2="220" y2="20"/>
      <line x1="0" y1="0" x2="0" y2="220"/>
      <line x1="20" y1="0" x2="20" y2="220"/>
      <path fill="#aaa" d="M100,20 c-40,0 -80,40 -80,80z"/>
      <path fill="#aaa" d="M100,21 c-39.5,0 -79,39.5 -79,79z"/>
      <path fill="#aaa" d="M100,22 c-39,0 -78,39 -78,78z"/>
      <path fill="none" stroke="#111" d="M100,20 c-40,0 -80,40 -80,80z"/>
      <path fill="none" stroke="#111" d="M120,60 c-20,0 -40,20 -40,40z"/>
    </svg>'''

    geometry = parse_ring_svg(svg)

    assert geometry.outer_radius_squared == 16
    assert geometry.inner_radius_squared == 4
    assert geometry.alignment == "offset"
