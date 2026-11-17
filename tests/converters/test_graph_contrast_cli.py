"""Command-line options for the contrast graph converter."""

from solution_runner.converters.graph_png_to_svg_by_contrast import _create_parser


def test_graph_cli_preserves_render_and_extraction_options():
    args = _create_parser().parse_args(
        [
            "graph.png",
            "--path-mode",
            "cubic",
            "--endpoint-style",
            "open",
            "--foreground-threshold",
            "0.4",
            "--no-labels",
            "--x-min",
            "-2",
            "--x-max",
            "3",
        ]
    )
    assert args.source == "graph.png"
    assert args.path_mode == "cubic"
    assert args.endpoint_style == "open"
    assert args.foreground_threshold == 0.4
    assert args.no_labels
    assert (args.x_min, args.x_max) == (-2, 3)
    assert args.cell_size == 20.0
