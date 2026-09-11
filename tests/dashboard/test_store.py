import json
from types import SimpleNamespace

import pytest

from solution_runner.dashboard.store import DashboardStore, sync_groups
from solution_runner.group_inventory_store import (
    GroupInventoryItem,
    GroupInventorySnapshot,
    GroupInventoryStore,
    GroupItemStageResult,
)


def _profile(group_key: str, catalog_snapshot_id: str = "catalog-1"):
    return SimpleNamespace(
        group_key=group_key,
        catalog_snapshot_id=catalog_snapshot_id,
        theme_title="Иррациональные уравнения",
        workflow_kind="content_rule",
        content_rule_key="irrational-test",
        strategy_key=None,
    )


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_sync_uses_latest_run_and_preserves_manual_state(tmp_path):
    runs = tmp_path / "var" / "equations" / "runs"
    old = runs / "20260101T000000Z-group-123"
    latest = runs / "20260102T000000Z-group-123"
    _write_json(old / "summary.json", {"group_key": "123", "targets": 2, "status": "completed"})
    _write_json(latest / "summary.json", {"group_key": "123", "targets": 3, "status": "completed"})
    _write_json(latest / "apply-results.json", {
        "results": [
            {"status": "applied"},
            {"status": "applied"},
            {"status": "already_complete"},
        ]
    })
    _write_json(latest / "helpers-results.json", [
        {"status": "applied"},
        {"status": "already_complete"},
        {"status": "applied"},
    ])

    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    report = sync_groups(store, {"123": _profile("123")}, tmp_path / "var")
    group = store.get_group("123")

    assert report["groups"] == 1
    assert group["total"] == 3
    assert group["transformed"] == 3
    assert group["helpers"] == 3
    assert group["column"] == "done"

    store.add_comment("123", "Раскрыть вычисление в решении")
    store.update_group("123", {"column": "review", "task_title": "Проверить группу"})
    sync_groups(store, {"123": _profile("123")}, tmp_path / "var")

    group = store.get_group("123")
    assert group["column"] == "review"
    assert group["task_title"] == "Проверить группу"
    assert store.list_comments("123")[0]["body"] == "Раскрыть вычисление в решении"


def test_store_persists_codex_thread_and_full_group_review_state(tmp_path):
    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")

    group = store.update_group("123", {
        "codex_thread_id": "thread-123",
        "task_title": "Регистрация группы 123",
        "full_dry_run_status": "ready",
    })

    assert group["codex_thread_id"] == "thread-123"
    assert group["task"] == "Регистрация группы 123"
    assert group["full_dry_run_status"] == "ready"


def test_comments_from_issues_and_review_return_group_to_work(tmp_path):
    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")

    for column in ("issues", "review"):
        store.update_group("123", {"column": column, "revision_requested": 0, "full_dry_run_status": "ready"})
        store.add_comment("123", f"Комментарий из {column}")
        group = store.get_group("123")
        assert group["column"] == "work"
        assert group["revision_requested"] is True
        assert group["full_dry_run_status"] is None


def test_sync_does_not_replace_group_totals_with_a_later_targeted_dry_run(tmp_path):
    runs = tmp_path / "var" / "equations" / "runs"
    applied = runs / "20260101T000000Z-group-123"
    dry_run = runs / "20260102T000000Z-group-123"
    targeted_apply = runs / "20260103T000000Z-group-123"
    _write_json(applied / "summary.json", {
        "group_key": "123", "targets": 3, "status": "completed", "apply": True,
    })
    _write_json(applied / "solution-results.json", [
        {"status": "applied"}, {"status": "applied"}, {"status": "applied"},
    ])
    _write_json(applied / "helpers-results.json", [
        {"status": "applied"}, {"status": "applied"}, {"status": "applied"},
    ])
    _write_json(dry_run / "summary.json", {
        "group_key": "123", "targets": 1, "status": "completed", "apply": False,
    })
    _write_json(dry_run / "solution-results.json", [{"status": "prepared"}])
    _write_json(targeted_apply / "summary.json", {
        "group_key": "123", "targets": 1, "status": "completed",
        "apply": True, "targeted": True,
    })
    _write_json(targeted_apply / "solution-results.json", [{"status": "applied"}])

    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    sync_groups(store, {"123": _profile("123")}, tmp_path / "var")

    group = store.get_group("123")
    assert group["total"] == 3
    assert group["transformed"] == 3


def test_sync_uses_sqlite_inventory_as_registered_group_source_of_truth(tmp_path):
    run = tmp_path / "var" / "equations" / "runs" / "20260103T000000Z-group-123"
    _write_json(run / "summary.json", {
        "group_key": "123", "targets": 1, "status": "completed", "apply": True,
    })
    _write_json(run / "solution-results.json", [{"status": "applied"}])
    _write_json(run / "helpers-results.json", [{"status": "applied"}])

    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    inventory = GroupInventoryStore(store.path)
    inventory.replace(GroupInventorySnapshot(
        group_key="123",
        catalog_snapshot_id="catalog-1",
        source_group_id="source-group",
        parent_problem_id="problem-1",
        parent_source_problem_id="1",
        items=tuple(
            GroupInventoryItem(f"problem-{index}", str(index), index - 1, True, True, True)
            for index in range(1, 274)
        ),
    ))
    for index in range(1, 271):
        inventory.update_item_stage(GroupItemStageResult(
            group_key="123",
            problem_id=f"problem-{index}",
            apply_status="applied",
            helpers_status="applied",
        ))
    for index in range(271, 274):
        inventory.update_item_stage(GroupItemStageResult(
            group_key="123",
            problem_id=f"problem-{index}",
            apply_status="failed",
            error="condition does not match a registered numeric rational expression",
        ))

    sync_groups(
        store,
        {"123": _profile("123")},
        tmp_path / "var",
        inventory_store=inventory,
    )

    group = store.get_group("123")
    assert group["total"] == 273
    assert group["transformed"] == 270
    assert group["helpers"] == 270
    assert group["errors"] == 3


def test_sync_keeps_history_only_group_as_legacy(tmp_path):
    run = tmp_path / "var" / "grid-polygon" / "runs" / "20260101T000000Z-group-999"
    _write_json(run / "summary.json", {"group_key": "999", "targets": 4, "status": "completed"})

    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    sync_groups(store, {}, tmp_path / "var")

    group = store.get_group("999")
    assert group["registered"] is False
    assert group["legacy"] is True
    assert group["column"] == "review"


def test_manual_group_stays_in_initialization_after_sync(tmp_path):
    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("new-1", "41bc4d03-40cd-4407-8dea-df76e3f47ea8")

    sync_groups(store, {}, tmp_path / "var")

    group = store.get_group("new-1")
    assert group["title"] == "Группа new-1"
    assert group["registered"] is False
    assert group["legacy"] is False
    assert group["source_id"] == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
    assert group["column"] == "initialization"
    assert group["existing_solution_policy"] == "preserve"
    assert group["condition_image_policy"] == "auto"
    assert group["solution_image_policy"] == "auto"
    assert group["verify_answers"] is True
    assert group["verify_helpers"] is True
    assert group["agent_sample_size"] == 1


def test_catalog_snapshots_get_distinct_filter_labels(tmp_path):
    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    profiles = {
        "main": _profile("main", "41bc4d03-40cd-4407-8dea-df76e3f47ea8"),
        "ege": _profile("ege", "4073fc7b-2056-4697-b18b-38741c94d0f4"),
        "oge": _profile("oge", "fd733f80-43d2-4b4a-b903-2423796cbee5"),
    }

    sync_groups(store, profiles, tmp_path / "var")

    labels = {group["id"]: group["source"] for group in store.list_groups()}
    assert labels == {
        "main": "Каталог ЕГЭ МАТ ПРОФИЛЬ",
        "ege": "Каталог ЕГЭ МАТ БАЗА",
        "oge": "Каталог ОГЭ МАТ",
    }


def test_review_comment_returns_group_to_work_for_agent(tmp_path):
    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("new-1", "41bc4d03-40cd-4407-8dea-df76e3f47ea8")
    store.update_group("new-1", {"column": "review"})

    store.add_comment("new-1", "Исправить картинку решения")

    group = store.get_group("new-1")
    assert group["column"] == "work"
    assert group["revision_requested"] is True

    store.update_group("new-1", {"column": "review"})
    assert store.get_group("new-1")["revision_requested"] is False


def test_manual_group_cannot_replace_registered_group(tmp_path):
    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    sync_groups(store, {"123": _profile("123")}, tmp_path / "var")

    with pytest.raises(ValueError, match="already exists"):
        store.add_manual_group("123", "another-catalog")

    assert store.get_group("123")["registered"] is True


def test_reconcile_problem_counts_uses_current_task_index(tmp_path):
    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    sync_groups(store, {"123": _profile("123")}, tmp_path / "var")

    store.reconcile_problem_counts("123", [
        {"apply_status": "applied", "helpers_status": "applied"},
        {"apply_status": "applied", "helpers_status": "failed"},
        {"apply_status": "blocked", "helpers_status": "skipped"},
    ])

    group = store.get_group("123")
    assert group["total"] == 3
    assert group["transformed"] == 2
    assert group["helpers"] == 1
    assert group["errors"] == 1
    assert group["blocked"] == 1
    assert group["stats"]["errors"] == 2
    assert group["column"] == "issues"
