import json
from pathlib import Path
from types import SimpleNamespace

import solution_runner.dashboard.dry_runs as dry_runs_module
from solution_runner.dashboard.dry_runs import (
    DryRunManager,
    _full_dry_run_ready,
    _launcher_command,
    _select_problem,
    _store_dry_run_results,
)
from solution_runner.group_inventory_store import (
    GroupInventoryItem,
    GroupInventorySnapshot,
    GroupInventoryStore,
)


def _profile():
    return SimpleNamespace(
        group_key="123",
        catalog_snapshot_id="catalog",
        source_group_id="source-group",
        workflow_kind="content_rule",
        solution_scope="all",
    )


def test_launcher_command_has_three_scopes_and_never_applies():
    profile = _profile()

    inventory_db = Path("dashboard.sqlite3")
    parent = _launcher_command(profile, "parent", "parent-uuid", inventory_db)
    random = _launcher_command(profile, "random", "child-uuid", inventory_db)
    entire_group = _launcher_command(profile, "all", None, inventory_db)

    assert "--apply" not in parent + random + entire_group
    assert parent[-2:] == ["--only-problem-id", "parent-uuid"]
    assert random[-2:] == ["--only-problem-id", "child-uuid"]
    assert "--only-problem-id" not in entire_group
    assert all("--inventory-db" in command for command in (parent, random, entire_group))


def test_problem_selection_uses_parent_or_one_saved_random_child():
    children = [
        {"uuid": "parent", "name": "Задача 10"},
        {"uuid": "child-a", "name": "Задача 11"},
        {"uuid": "child-b", "name": "Задача 12"},
    ]

    assert _select_problem(children, "parent", choose=lambda items: items[-1]) == children[0]
    assert _select_problem(children, "random", choose=lambda items: items[-1]) == children[2]
    assert _select_problem(children, "all", choose=lambda items: items[-1]) is None


def test_problem_selection_uses_one_explicit_problem_without_random_choice():
    children = [
        {"uuid": "parent", "name": "Задача 10"},
        {"uuid": "child", "name": "Задача 11"},
    ]

    selected = _select_problem(
        children,
        "problem",
        requested_problem_id="child",
        choose=lambda _items: (_ for _ in ()).throw(AssertionError("must not choose")),
    )

    assert selected == children[1]


def test_random_problem_selection_excludes_samples_already_in_the_preview():
    children = [
        {"uuid": "parent", "name": "Задача 10"},
        {"uuid": "shown", "name": "Задача 11"},
        {"uuid": "next", "name": "Задача 12"},
    ]

    selected = _select_problem(
        children,
        "random",
        choose=lambda items: items[0],
        excluded_problem_ids={"shown"},
    )

    assert selected["uuid"] == "next"


def test_problem_selection_accepts_the_real_mcp_children_envelope():
    payload = {
        "parent_id": "source-group",
        "parent_type": "group",
        "children": [
            {
                "problem_id": "parent",
                "source_problem_id": "10",
                "name": "Задача 10",
            },
            {
                "problem_id": "child",
                "source_problem_id": "11",
                "name": "Задача 11",
            },
        ],
    }

    assert _select_problem(payload, "parent")["problem_id"] == "parent"


def test_dry_run_records_update_per_problem_status_without_apply_state(tmp_path):
    store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    store.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="10",
        items=(
            GroupInventoryItem("parent", "10", 0, True, True, True),
            GroupInventoryItem("child", "11", 1, True, False, True),
        ),
    ))

    _store_dry_run_results(store, "123", {"records": [
        {"problem_id": "parent", "status": "prepared"},
        {"problem_id": "child", "status": "blocked", "message": "unsupported grammar"},
    ]})

    rows = {row["problem_id"]: row for row in store.list_items("123")}
    assert rows["parent"]["dry_run_status"] == "ready"
    assert rows["parent"]["apply_status"] is None
    assert rows["child"]["dry_run_status"] == "skipped"
    assert rows["child"]["error"] == "unsupported grammar"


def test_full_group_review_requires_every_manifest_record_to_be_ready():
    assert _full_dry_run_ready({"records": [
        {"status": "prepared"}, {"status": "already_complete"},
    ]}) is True
    assert _full_dry_run_ready({"records": [
        {"status": "prepared"}, {"status": "blocked"},
    ]}) is False


def test_manager_persists_selected_problem_before_launch(tmp_path):
    launched = []
    manager = DryRunManager(
        var_dir=tmp_path,
        profiles={"123": _profile()},
        gateway_factory=lambda: SimpleNamespace(
            get_source_catalog_children=lambda *_: [
                {"uuid": "parent", "name": "Задача 10"},
                {"uuid": "child", "name": "Задача 11"},
            ],
            close=lambda: None,
        ),
        launcher=lambda command: launched.append(command) or 1,
        choose=lambda items: items[-1],
    )

    manager.run_now("123", "random")

    state = json.loads((tmp_path / "dashboard/dry-runs/123.json").read_text())
    assert state["mode"] == "random"
    assert state["selected_problem_id"] == "child"
    assert state["selected_source_problem_id"] == "11"
    assert state["status"] == "failed"
    assert launched[0][-2:] == ["--only-problem-id", "child"]


def test_manager_runs_one_explicit_initialized_problem(tmp_path):
    launched = []
    inventory_store = GroupInventoryStore(tmp_path / "dashboard.sqlite3")
    inventory_store.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="10",
        items=(
            GroupInventoryItem("parent", "10", 0, True, True, True),
            GroupInventoryItem("child", "11", 1, True, False, True),
        ),
    ))
    manager = DryRunManager(
        var_dir=tmp_path,
        profiles={"123": _profile()},
        gateway_factory=lambda: SimpleNamespace(close=lambda: None),
        inventory_store=inventory_store,
        launcher=lambda command: launched.append(command) or 1,
    )

    state = manager.run_now("123", "problem", requested_problem_id="child")

    assert state["selected_problem_id"] == "child"
    assert state["selected_source_problem_id"] == "11"
    assert launched[0][-2:] == ["--only-problem-id", "child"]


def test_failed_full_group_dry_run_moves_group_to_issues(tmp_path):
    updates = []
    manager = DryRunManager(
        var_dir=tmp_path,
        profiles={"123": _profile()},
        gateway_factory=lambda: SimpleNamespace(close=lambda: None),
        store=SimpleNamespace(
            update_group=lambda group_key, changes: updates.append((group_key, changes))
        ),
        launcher=lambda _command: 2,
    )

    manager.run_now("123", "all")

    assert updates == [("123", {"column": "issues", "full_dry_run_status": "failed"})]


def test_failed_targeted_dry_run_does_not_move_group(tmp_path):
    updates = []
    manager = DryRunManager(
        var_dir=tmp_path,
        profiles={"123": _profile()},
        gateway_factory=lambda: SimpleNamespace(close=lambda: None),
        store=SimpleNamespace(
            update_group=lambda group_key, changes: updates.append((group_key, changes))
        ),
        launcher=lambda _command: 2,
    )

    manager.run_now("123", "problem", requested_problem_id="problem")

    assert updates == []


def test_full_group_dry_run_moves_to_review_only_when_every_record_is_ready(tmp_path, monkeypatch):
    updates = []
    manifest = {"group_key": "123", "records": [{
        "problem_id": "problem", "source_problem_id": "10",
        "status": "prepared", "transformations": [],
    }]}
    monkeypatch.setattr(dry_runs_module, "latest_dry_run_manifest", lambda *_: manifest)
    monkeypatch.setattr(dry_runs_module, "fetch_preview", lambda *_: {"group_key": "123", "samples": []})
    manager = DryRunManager(
        var_dir=tmp_path,
        profiles={"123": _profile()},
        gateway_factory=lambda: SimpleNamespace(close=lambda: None),
        store=SimpleNamespace(update_group=lambda group_key, changes: updates.append((group_key, changes))),
        launcher=lambda _command: 0,
    )

    state = manager.run_now("123", "all")

    assert state["status"] == "completed"
    assert updates == [("123", {"column": "review", "full_dry_run_status": "ready"})]

    manifest["records"][0]["status"] = "blocked"
    state = manager.run_now("123", "all")
    assert state["status"] == "completed_with_errors"
    assert updates[-1] == ("123", {"column": "issues", "full_dry_run_status": "failed"})


def test_missing_only_group_without_candidates_is_skipped_without_launch(tmp_path):
    profile = SimpleNamespace(
        **{**vars(_profile()), "workflow_kind": "geometry", "solution_scope": "missing_only"}
    )
    manager = DryRunManager(
        var_dir=tmp_path,
        profiles={"123": profile},
        gateway_factory=lambda: SimpleNamespace(
            get_source_catalog_children=lambda *_: {
                "items": [{"uuid": "parent", "name": "Задача 10"}]
            },
            get_source_catalog_missing_solution_summary=lambda *_: {
                "source_problem_ids": []
            },
            close=lambda: None,
        ),
        launcher=lambda _command: (_ for _ in ()).throw(
            AssertionError("launcher must not run without an eligible target")
        ),
    )

    state = manager.run_now("123", "random")

    assert state["status"] == "skipped"
    assert state["message"] == "В группе нет задач, которые этот раннер должен изменять."
