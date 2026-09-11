from solution_runner.group_inventory_store import (
    GroupInventoryAsset,
    GroupInventoryItem,
    GroupInventorySnapshot,
    GroupInventoryStore,
    GroupItemStageResult,
)


def _snapshot() -> GroupInventorySnapshot:
    return GroupInventorySnapshot(
        group_key="27591",
        catalog_snapshot_id="catalog",
        source_group_id="source-group",
        parent_problem_id="problem-parent",
        parent_source_problem_id="55259",
        items=(
            GroupInventoryItem("problem-parent", "55259", 0, True, True, True),
            GroupInventoryItem("problem-child", "55260", 1, True, False, True),
        ),
        assets=(
            GroupInventoryAsset(
                "problem-parent", "asset-1", "image_1", "condition", "image/svg+xml"
            ),
        ),
    )


def test_replace_inventory_round_trips_canonical_problem_ids(tmp_path):
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")

    store.replace(_snapshot())

    assert store.get("27591") == _snapshot()


def test_failed_refresh_keeps_last_ready_items_and_stage_results(tmp_path):
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    store.replace(_snapshot())
    store.update_item_stage(
        GroupItemStageResult(
            group_key="27591",
            problem_id="problem-child",
            dry_run_status="completed",
            helpers_status="ready",
        )
    )

    store.set_status("27591", "failed", "source group disappeared")

    snapshot = store.get("27591")
    assert snapshot is not None
    assert snapshot.status == "failed"
    assert snapshot.error == "source group disappeared"
    assert [item.problem_id for item in snapshot.items] == [
        "problem-parent",
        "problem-child",
    ]
    assert store.list_items("27591")[1]["dry_run_status"] == "completed"


def test_successful_dry_run_does_not_clear_an_unresolved_helpers_error(tmp_path):
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    store.replace(_snapshot())
    store.update_item_stage(GroupItemStageResult(
        group_key="27591", problem_id="problem-child",
        apply_status="applied", helpers_status="failed", error="write fence is busy",
    ))

    store.update_item_stage(GroupItemStageResult(
        group_key="27591", problem_id="problem-child", dry_run_status="ready",
    ))

    row = store.list_items("27591")[1]
    assert row["helpers_status"] == "failed"
    assert row["error"] == "write fence is busy"


def test_successful_helpers_retry_clears_the_resolved_error(tmp_path):
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    store.replace(_snapshot())
    store.update_item_stage(GroupItemStageResult(
        group_key="27591", problem_id="problem-child",
        helpers_status="failed", error="write fence is busy",
    ))

    store.update_item_stage(GroupItemStageResult(
        group_key="27591", problem_id="problem-child", helpers_status="applied",
    ))

    row = store.list_items("27591")[1]
    assert row["helpers_status"] == "applied"
    assert row["error"] is None
