"""Check the artifacts written by the extrema graph converter."""

import json

from solution_runner.converters import graph_png_to_svg_by_extrema as extrema


def test_writes_svg_diagnostics_and_optional_overlay(tmp_path, monkeypatch):
    svg = tmp_path / "graph.svg"
    diagnostics = tmp_path / "graph.json"
    overlay = tmp_path / "graph.debug.png"
    image, grid, trace, fit = (object() for _ in range(4))
    calls = []
    monkeypatch.setattr(
        extrema,
        "diagnostics_payload",
        lambda source, rgba, actual_grid, actual_trace, actual_fit, **kwargs: {
            "source": source,
            "threshold": kwargs["foreground_threshold"],
        },
    )
    monkeypatch.setattr(extrema, "save_debug_overlay", lambda *args: calls.append(args))

    extrema._write_result(
        (svg, diagnostics, overlay),
        "source.png",
        "<svg/>",
        (image, grid, trace, fit),
        0.2,
    )

    assert svg.read_text() == "<svg/>"
    assert json.loads(diagnostics.read_text()) == {
        "source": "source.png",
        "threshold": 0.2,
    }
    assert calls == [(image, grid, trace, fit, overlay)]
