"""Check label generation for graphs with tangents."""

from solution_runner.converters.graph_contrast_tangent_svg import _tangent_labels


def test_labels_include_guide_and_escaped_graph_name():
    labels, ticks = _tangent_labels(
        (20, 80, 200, 100, 20),
        (50, 40),
        (60, 80),
        ("f&lt;x&gt;", "x₀", "#143b8f"),
        True,
    )
    assert "f&lt;x&gt;" in labels
    assert "x₀" in labels
    assert 'fill="#143b8f"' in labels
    assert "<path d=" in ticks
    assert _tangent_labels(
        (20, 80, 200, 100, 20), (50, 40), (60, 80), ("f", "x₀", "blue"), False
    ) == ("", "")
