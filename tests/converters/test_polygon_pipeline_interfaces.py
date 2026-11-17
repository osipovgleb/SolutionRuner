"""Keep the conversion and rollback entry points callable by existing clients."""

from inspect import signature

from solution_runner.converters import (
    mcp_grid_polygon_transformations,
    mcp_polygon_operations,
    mcp_polygon_rollback,
)


def test_candidate_entry_points_keep_keyword_arguments():
    expected = {
        "client",
        "candidate",
        "converter",
        "converter_fingerprint",
        "template_path",
        "run_dir",
        "transfer_timeout_seconds",
        "logger",
    }
    assert (
        expected
        <= signature(
            mcp_grid_polygon_transformations.prepare_candidate
        ).parameters.keys()
    )
    assert (
        expected | {"services"}
        == signature(mcp_polygon_operations.prepare_candidate).parameters.keys()
    )


def test_rollback_entry_point_keeps_keyword_arguments():
    assert set(signature(mcp_polygon_rollback.finish_rollback_run).parameters) == {
        "client",
        "args",
        "run_dir",
        "logger",
        "user_id",
        "source_site_id",
        "scope",
    }
