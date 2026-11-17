"""Check the graph converter's user-facing artifact report."""

from types import SimpleNamespace

from solution_runner.converters.graph_contrast_report import report_outputs


def test_report_lists_geometry_and_optional_artifacts(capsys):
    grid = SimpleNamespace(vertical=SimpleNamespace(step=2), horizontal=SimpleNamespace(step=3), vertical_axis_x=4, horizontal_axis_y=5)
    endpoint = SimpleNamespace(logical_x=1, logical_y=2)
    trace = SimpleNamespace(start=endpoint, end=endpoint, tangent=SimpleNamespace(logical_slope=0.5))
    interval = SimpleNamespace(left=-1, right=1)
    report_outputs(("a.svg", "a.json", "a.png"), (grid, trace), ("f", "single_curve", interval))
    assert capsys.readouterr().out.splitlines() == [
        "svg=a.svg", "diagnostics=a.json", "debug_overlay=a.png", "grid_step=(2, 3)",
        "axes=(vertical_x=4, horizontal_y=5)", "curve_endpoints=[(1, 2), (1, 2)]",
        "graph_label=f", "diagram_kind=single_curve", "tangent_slope=0.5",
        "condition_x_interval=(-1, 1)",
    ]
