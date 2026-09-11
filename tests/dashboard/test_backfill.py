import json
from types import SimpleNamespace

from solution_runner.dashboard.backfill import backfill_local_runs, backfill_mcp_inventory
from solution_runner.group_inventory_store import GroupInventoryStore
from solution_runner.group_inventory_store import GroupInventoryItem, GroupInventorySnapshot


def _write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_backfill_imports_manifest_identities_and_stage_results_as_partial(tmp_path):
    run = tmp_path / "var/grid-polygon/runs/20260910T000000Z-group-123"
    _write(run / "summary.json", {"group_key": "123", "targets": 2})
    _write(run / "prepared-manifest.json", {
        "group_key": "123", "catalog_snapshot_id": "catalog",
        "source_group_id": "source-group",
        "records": [
            {"problem_id": "parent", "source_problem_id": "10", "status": "prepared", "transformations": []},
            {"problem_id": "child", "source_problem_id": "11", "status": "blocked", "message": "unsupported"},
        ],
    })
    _write(run / "apply-results.json", [
        {"problem_id": "parent", "status": "applied"},
    ])
    _write(run / "helpers-results.json", {"results": [
        {"problem_id": "parent", "status": "already_complete"},
    ]})
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    profile = SimpleNamespace(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group"
    )

    report = backfill_local_runs(store, tmp_path / "var", {"123": profile})

    assert report == {"groups": 1, "tasks": 2, "skipped_ready": 0}
    snapshot = store.get("123")
    assert snapshot.status == "partial"
    assert snapshot.parent_problem_id == "parent"
    rows = {row["problem_id"]: row for row in store.list_items("123")}
    assert rows["parent"]["dry_run_status"] == "ready"
    assert rows["parent"]["apply_status"] == "applied"
    assert rows["parent"]["helpers_status"] == "already_complete"
    assert rows["child"]["dry_run_status"] == "skipped"
    assert rows["child"]["error"] == "unsupported"


def test_mcp_backfill_skips_ready_and_initializes_incomplete_groups(tmp_path):
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    store.set_status("ready", "ready")
    store.set_status("partial", "partial")

    class Initializer:
        def __init__(self):
            self.calls = []

        def run_now(self, group_key):
            self.calls.append(group_key)
            status = "failed" if group_key == "broken" else "ready"
            store.set_status(group_key, status, "nope" if status == "failed" else None)
            return {"status": status, "total": 2 if status == "ready" else 0}

    initializer = Initializer()
    report = backfill_mcp_inventory(
        store,
        {key: object() for key in ("ready", "partial", "new", "broken")},
        initializer,
    )

    assert initializer.calls == ["partial", "new", "broken"]
    assert report == {"ready": 2, "failed": 1, "tasks": 4, "skipped_ready": 1}


def test_backfill_never_replaces_a_ready_initialized_inventory(tmp_path):
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    store.set_status("123", "ready")

    report = backfill_local_runs(store, tmp_path / "var", {})

    assert report["skipped_ready"] == 0
    assert store.get("123").status == "ready"


def test_backfill_replays_apply_failures_for_ready_inventory_without_dry_run_overwrite(tmp_path):
    apply_run = tmp_path / "var/runs/20260907T000000Z-group-123"
    dry_run = tmp_path / "var/runs/20260908T000000Z-group-123"
    _write(apply_run / "summary.json", {"group_key": "123", "apply": True})
    _write(apply_run / "solution-results.json", [
        {"problem_id": "child", "status": "applied"},
    ])
    _write(apply_run / "helpers-results.json", [
        {"problem_id": "child", "status": "failed", "message": "write fence is busy"},
    ])
    _write(dry_run / "summary.json", {"group_key": "123", "apply": False})
    _write(dry_run / "solution-results.json", [
        {"problem_id": "child", "status": "planned"},
    ])
    _write(dry_run / "helpers-results.json", [
        {"problem_id": "child", "status": "planned"},
    ])
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    store.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="child", parent_source_problem_id="11",
        items=(GroupInventoryItem("child", "11", 0, True, True, True),),
    ))
    profile = SimpleNamespace(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group"
    )

    backfill_local_runs(store, tmp_path / "var", {"123": profile})

    row = store.list_items("123")[0]
    assert row["apply_status"] == "applied"
    assert row["helpers_status"] == "failed"
    assert row["error"] == "write fence is busy"


def test_backfill_keeps_primary_solution_error_when_helpers_was_skipped(tmp_path):
    run = tmp_path / "var/runs/20260907T000000Z-group-123"
    _write(run / "summary.json", {"group_key": "123", "apply": True})
    _write(run / "solution-results.json", [{
        "problem_id": "child", "status": "failed",
        "message": "condition wording does not match selector",
    }])
    _write(run / "helpers-results.json", [{
        "problem_id": "child", "status": "skipped",
        "message": "ineligible upstream solution_answer:failed",
    }])
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    store.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="child", parent_source_problem_id="11",
        items=(GroupInventoryItem("child", "11", 0, True, False, True),),
    ))
    profile = SimpleNamespace(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group"
    )

    backfill_local_runs(store, tmp_path / "var", {"123": profile})

    row = store.list_items("123")[0]
    assert row["error"] == "condition wording does not match selector"
