"""Verify selection of fresh and resumed polygon worklists."""

from types import SimpleNamespace
from unittest.mock import Mock

from solution_runner.converters.mcp_polygon_run_state import (
    InventoryContext,
    prepare_inventory,
)


def test_inventory_resume_passes_frozen_scope_and_renderer(tmp_path):
    args = SimpleNamespace(
        resume_from_run=tmp_path / "old",
        catalog_snapshot_id="catalog",
        category_key="9",
        theme_titles=("theme",),
        resume_preserve_applied=True,
    )
    context = InventoryContext(
        tmp_path / "new", "site", [("theme", [])], "converter", "template", Mock()
    )
    resume, build = Mock(return_value=({"group": "inventory"}, {"tasks": 2})), Mock()
    assert prepare_inventory(args, Mock(), context, (resume, build)) == (
        {"group": "inventory"},
        {"tasks": 2},
    )
    assert resume.call_args.kwargs["source_run_dir"] == args.resume_from_run
    assert resume.call_args.kwargs["scope"] == context.scope
    assert resume.call_args.kwargs["converter_fingerprint"] == "converter"
    assert resume.call_args.kwargs["template_fingerprint"] == "template"
    assert resume.call_args.kwargs["preserve_applied"] is True
    build.assert_not_called()


def test_new_inventory_builds_with_requested_scope(tmp_path):
    args = SimpleNamespace(
        resume_from_run=None,
        catalog_snapshot_id="catalog",
        category_key="9",
        category_title="Geometry",
        theme_titles=("theme",),
        mode="inventory",
    )
    context = InventoryContext(
        tmp_path, "site", [("theme", [])], "converter", "template", Mock()
    )
    client, resume, build = Mock(), Mock(), Mock(return_value=({}, {}))
    assert prepare_inventory(args, client, context, (resume, build)) == ({}, {})
    assert build.call_args.args == (client,)
    assert build.call_args.kwargs["scope"] == context.scope
    assert build.call_args.kwargs["mode"] == "inventory"
    resume.assert_not_called()
