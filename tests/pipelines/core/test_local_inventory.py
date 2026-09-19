from types import SimpleNamespace

import pytest

from solution_runner.group_inventory_store import (
    GroupInventoryAsset,
    GroupInventoryItem,
    GroupInventorySnapshot,
    GroupInventoryStore,
)
from solution_runner.pipelines.core.local_inventory import load_group_inventory


def _profile(**changes):
    values = {
        "group_key": "123",
        "catalog_snapshot_id": "catalog",
        "source_group_id": "source-group",
        "workflow_kind": "geometry",
        "solution_scope": "all",
    }
    values.update(changes)
    return SimpleNamespace(**values)


def _store(tmp_path):
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    store.replace(GroupInventorySnapshot(
        group_key="123",
        catalog_snapshot_id="catalog",
        source_group_id="source-group",
        parent_problem_id="parent",
        parent_source_problem_id="10",
        items=(
            GroupInventoryItem("parent", "10", 0, True, True, True),
            GroupInventoryItem("child", "11", 1, True, False, True),
            GroupInventoryItem(
                "unavailable", "12", 2, False, False, False,
                content_status="unavailable", inventory_error="missing normalized",
            ),
        ),
        assets=(
            GroupInventoryAsset("parent", "a", "image_1", "condition", "image/svg+xml"),
            GroupInventoryAsset("child", "b", "image_1", "condition", "image/png"),
        ),
    ))
    return store


def test_local_geometry_inventory_uses_saved_order_and_image_types(tmp_path):
    inventory = load_group_inventory(_store(tmp_path), _profile())

    assert [target.problem_id for target in inventory.targets] == ["parent", "child"]
    assert [target.problem_id for target in inventory.png_targets] == ["child"]
    assert [target.problem_id for target in inventory.svg_targets] == ["parent"]


def test_local_inventory_applies_solution_scope_without_mcp_discovery(tmp_path):
    inventory = load_group_inventory(
        _store(tmp_path),
        _profile(workflow_kind="content_rule", solution_scope="missing_only"),
    )

    assert [target.problem_id for target in inventory.targets] == ["child"]
    assert inventory.png_targets == ()
    assert inventory.svg_targets == ()

    complete = load_group_inventory(
        _store(tmp_path),
        _profile(workflow_kind="content_rule", solution_scope="missing_only"),
        apply_solution_scope=False,
    )
    assert [target.problem_id for target in complete.targets] == ["parent", "child"]


def test_local_inventory_allows_assetless_helpers_scope(tmp_path):
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    store.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="10",
        items=(GroupInventoryItem("parent", "10", 0, True, True, True),),
    ))

    inventory = load_group_inventory(store, _profile(), apply_solution_scope=False)

    assert [target.problem_id for target in inventory.targets] == ["parent"]


def test_local_inventory_rejects_stale_group_coordinates(tmp_path):
    with pytest.raises(ValueError, match="does not match"):
        load_group_inventory(_store(tmp_path), _profile(source_group_id="other"))
