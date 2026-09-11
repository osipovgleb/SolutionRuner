import json
from types import SimpleNamespace

import pytest

from solution_runner.dashboard.applies import ApplyManager
from solution_runner.dashboard.store import DashboardStore
from solution_runner.group_inventory_store import (
    GroupInventoryItem,
    GroupInventorySnapshot,
    GroupInventoryStore,
    GroupItemStageResult,
)


def test_apply_requires_successful_dry_run_for_exact_problem(tmp_path):
    inventory = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    inventory.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="10",
        items=(GroupInventoryItem("child", "11", 0, True, False, True),),
    ))
    manager = ApplyManager(
        var_dir=tmp_path,
        profiles={"123": SimpleNamespace(group_key="123", catalog_snapshot_id="catalog")},
        inventory_store=inventory,
        executor=lambda _args: (_ for _ in ()).throw(AssertionError("must not apply")),
    )

    with pytest.raises(ValueError, match="successful dry-run"):
        manager.start("123", "child")


def test_group_apply_requires_a_successful_full_group_dry_run(tmp_path):
    inventory = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")
    inventory.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="10",
        items=(GroupInventoryItem("child", "11", 0, True, False, True),),
    ))
    inventory.update_item_stage(GroupItemStageResult(
        group_key="123", problem_id="child", dry_run_status="ready",
    ))
    manager = ApplyManager(
        var_dir=tmp_path,
        profiles={"123": SimpleNamespace(group_key="123", catalog_snapshot_id="catalog")},
        inventory_store=inventory,
        store=store,
        executor=lambda _args: (_ for _ in ()).throw(AssertionError("must not apply")),
    )

    with pytest.raises(ValueError, match="full-group dry-run"):
        manager.start_group("123")

    store.update_group("123", {"full_dry_run_status": "ready"})
    manager.executor.submit = lambda function, *args: None
    assert manager.start_group("123")["status"] == "queued"


@pytest.mark.parametrize(("apply_status", "helpers_status"), [
    ("failed", "skipped"),
    ("applied", "failed"),
])
def test_any_failed_exact_problem_can_be_retried_without_a_new_dry_run(
    tmp_path, apply_status, helpers_status,
):
    inventory = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    inventory.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="10",
        items=(GroupInventoryItem("child", "11", 0, True, False, True),),
    ))
    inventory.update_item_stage(GroupItemStageResult(
        group_key="123", problem_id="child",
        apply_status=apply_status, helpers_status=helpers_status, error="pipeline failed",
    ))
    calls = []
    manager = ApplyManager(
        var_dir=tmp_path,
        profiles={"123": SimpleNamespace(group_key="123", catalog_snapshot_id="catalog")},
        inventory_store=inventory,
        executor=lambda args: calls.append(args) or 0,
    )
    manager.executor.submit = lambda function, *args: None

    state = manager.start("123", "child")

    assert state["status"] == "queued"
    assert state["problem_id"] == "child"


def test_apply_calls_shared_executor_for_only_the_verified_problem(tmp_path):
    inventory = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")
    store.update_group("123", {"column": "issues"})
    inventory.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="10",
        items=(GroupInventoryItem("child", "11", 0, True, False, True),),
    ))
    inventory.update_item_stage(GroupItemStageResult(
        group_key="123", problem_id="child", dry_run_status="ready",
    ))
    calls = []

    def execute(args):
        calls.append(args)
        run = tmp_path / "content-rule/runs/20260911T000000Z-group-123"
        run.mkdir(parents=True)
        (run / "summary.json").write_text(json.dumps({
            "group_key": "123", "status": "completed", "targets": 1,
            "failed_stage_results": 0,
        }))
        (run / "solution-results.json").write_text(json.dumps([{
            "problem_id": "child", "source_problem_id": "11",
            "stage": "solution_answer", "status": "applied",
        }]))
        (run / "helpers-results.json").write_text(json.dumps([{
            "problem_id": "child", "source_problem_id": "11",
            "stage": "helpers", "status": "applied",
        }]))
        return 0

    manager = ApplyManager(
        var_dir=tmp_path,
        profiles={"123": SimpleNamespace(group_key="123", catalog_snapshot_id="catalog")},
        inventory_store=inventory,
        store=store,
        executor=execute,
    )

    state = manager.run_now("123", "child")

    assert state["status"] == "completed"
    assert "--apply" in calls[0]
    assert calls[0][-2:] == ["--only-problem-id", "child"]
    row = inventory.list_items("123")[0]
    assert row["apply_status"] == "applied"
    assert row["helpers_status"] == "applied"
    assert store.get_group("123")["column"] == "review"


def test_apply_reports_primary_solution_error_when_helpers_is_skipped(tmp_path):
    inventory = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    inventory.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="10",
        items=(GroupInventoryItem("child", "11", 0, True, False, True),),
    ))
    inventory.update_item_stage(GroupItemStageResult(
        group_key="123", problem_id="child", dry_run_status="ready",
    ))

    def execute(_args):
        run = tmp_path / "content-rule/runs/20260911T000000Z-group-123"
        run.mkdir(parents=True)
        (run / "summary.json").write_text(json.dumps({
            "group_key": "123", "status": "completed_with_errors", "targets": 1,
            "failed_stage_results": 1,
        }))
        (run / "solution-results.json").write_text(json.dumps([{
            "problem_id": "child", "source_problem_id": "11",
            "stage": "solution_answer", "status": "failed",
            "message": "condition wording does not match selector",
        }]))
        (run / "helpers-results.json").write_text(json.dumps([{
            "problem_id": "child", "source_problem_id": "11",
            "stage": "helpers", "status": "skipped",
            "message": "ineligible upstream solution_answer:failed",
        }]))
        return 0

    manager = ApplyManager(
        var_dir=tmp_path,
        profiles={"123": SimpleNamespace(group_key="123", catalog_snapshot_id="catalog")},
        inventory_store=inventory,
        executor=execute,
    )

    manager.run_now("123", "child")

    assert inventory.list_items("123")[0]["error"] == "condition wording does not match selector"


def test_apply_group_uses_sqlite_inventory_and_projects_every_result(tmp_path):
    inventory = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")
    store.update_group("123", {"full_dry_run_status": "ready"})
    inventory.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="10",
        items=(
            GroupInventoryItem("parent", "10", 0, True, True, True),
            GroupInventoryItem("child", "11", 1, True, False, True),
        ),
    ))
    inventory.update_item_stage(GroupItemStageResult(
        group_key="123", problem_id="child", dry_run_status="ready",
    ))
    calls = []

    def execute(args):
        calls.append(args)
        run = tmp_path / "content-rule/runs/20260911T000000Z-group-123"
        run.mkdir(parents=True)
        (run / "summary.json").write_text(json.dumps({
            "group_key": "123", "status": "completed", "targets": 2,
            "failed_stage_results": 0,
        }))
        (run / "solution-results.json").write_text(json.dumps([
            {"problem_id": "parent", "status": "already_complete"},
            {"problem_id": "child", "status": "applied"},
        ]))
        (run / "helpers-results.json").write_text(json.dumps([
            {"problem_id": "parent", "status": "already_complete"},
            {"problem_id": "child", "status": "applied"},
        ]))
        return 0

    manager = ApplyManager(
        var_dir=tmp_path,
        profiles={"123": SimpleNamespace(group_key="123", catalog_snapshot_id="catalog")},
        inventory_store=inventory,
        store=store,
        executor=execute,
    )

    state = manager.run_group_now("123")

    assert state["status"] == "completed"
    assert state["scope"] == "group"
    assert "--apply" in calls[0]
    assert "--only-problem-id" not in calls[0]
    assert all(row["apply_status"] in {"applied", "already_complete"} for row in inventory.list_items("123"))
    assert all(row["helpers_status"] in {"applied", "already_complete"} for row in inventory.list_items("123"))


def test_apply_group_requires_a_successful_review_run(tmp_path):
    inventory = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    inventory.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="10",
        items=(GroupInventoryItem("parent", "10", 0, True, True, True),),
    ))
    manager = ApplyManager(
        var_dir=tmp_path,
        profiles={"123": SimpleNamespace(group_key="123", catalog_snapshot_id="catalog")},
        inventory_store=inventory,
        executor=lambda _args: (_ for _ in ()).throw(AssertionError("must not apply")),
    )

    with pytest.raises(ValueError, match="successful full-group dry-run"):
        manager.start_group("123")
