import json
from urllib.error import HTTPError
import pytest
from threading import Thread
from types import SimpleNamespace
from urllib.request import Request, urlopen

from solution_runner.dashboard.server import (
    _finish_automatic_dry_run,
    _finish_initialization,
    _handle_codex_exit,
    _resume_automatic_groups,
    make_server,
)
from solution_runner.dashboard.store import DashboardStore
from solution_runner.dashboard.previews import save_preview
from solution_runner.group_inventory_store import (
    GroupInventoryItem,
    GroupInventorySnapshot,
    GroupInventoryStore,
)


def _request(url, *, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(url, method=method, data=data, headers={"Content-Type": "application/json"})
    with urlopen(request) as response:
        return response.status, json.load(response)


def test_remove_group_rejects_active_work_and_preserves_inventory(tmp_path):
    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")
    inventory = GroupInventoryStore(store.path)
    inventory.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="10",
        items=(GroupInventoryItem("parent", "10", 0, True, True, True),),
    ))
    state = {"status": "running"}
    initializer = SimpleNamespace(get=lambda key: state)
    server = make_server(store=store, inventory_store=inventory, initializer=initializer,
                         var_dir=tmp_path / "var", profiles={}, static_dir=tmp_path, port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/api/groups/123"
    try:
        with pytest.raises(HTTPError) as error:
            _request(url, method="DELETE")
        assert error.value.code == 409
        state["status"] = "ready"
        store.update_group("123", {"agent_status": "working"})
        with pytest.raises(HTTPError) as error:
            _request(url, method="DELETE")
        assert error.value.code == 409
        store.update_group("123", {"agent_status": "blocked"})
        server.applies = SimpleNamespace(get=lambda key: {"status": "running"})
        with pytest.raises(HTTPError) as error:
            _request(url, method="DELETE")
        assert error.value.code == 409
        server.applies = None
        assert _request(url, method="DELETE") == (200, {"removed": True})
        assert store.get_group("123") is None
        assert len(inventory.get("123").items) == 1
        with pytest.raises(HTTPError) as error:
            _request(url, method="DELETE")
        assert error.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_ready_initialization_waits_for_manual_registration(tmp_path):
    class FakeCodexTasks:
        def register_group(self, group, inventory, thread_id=None):
            raise AssertionError("Initialization must not launch Codex")

    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("new-1", "catalog")
    inventory = GroupInventoryStore(store.path)
    inventory.replace(GroupInventorySnapshot(
        group_key="new-1", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="10",
        items=(GroupInventoryItem("parent", "10", 0, True, True, True),),
    ))

    _finish_initialization(store, inventory, FakeCodexTasks(), "new-1", {"status": "ready"})
    group = store.get_group("new-1")
    assert group["codex_thread_id"] is None
    assert group["agent_status"] is None
    assert group["column"] == "queue"
    assert "ручной регистрации" in group["agent_summary"]

    store.update_group("new-1", {"codex_thread_id": "thread-new", "agent_status": "working"})
    _handle_codex_exit(store, "thread-new", 0)
    group = store.get_group("new-1")
    assert group["agent_status"] == "needs_input"
    assert group["column"] == "issues"


def test_failed_codex_exit_does_not_override_agent_final_status(tmp_path):
    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")
    store.update_group("123", {
        "codex_thread_id": "thread-123",
        "agent_status": "updated",
        "agent_summary": "Полный dry-run готов.",
        "full_dry_run_status": "ready",
    })

    _handle_codex_exit(store, "thread-123", 1)

    assert store.get_group("123")["agent_status"] == "updated"


def test_agent_result_without_full_dry_run_is_verified_by_server(tmp_path):
    class FakeDryRuns:
        def __init__(self):
            self.started = []

        def start(self, group_key, mode):
            self.started.append((group_key, mode))

    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")
    store.update_group("123", {
        "codex_thread_id": "thread-123",
        "agent_status": "updated",
        "agent_summary": "Раннер исправлен.",
    })
    dry_runs = FakeDryRuns()

    _handle_codex_exit(store, "thread-123", 0, dry_runs)

    assert dry_runs.started == [("123", "all")]
    assert store.get_group("123")["agent_status"] == "verifying"

    _finish_automatic_dry_run(store, "123", {"mode": "all", "status": "completed"})
    group = store.get_group("123")
    assert group["agent_status"] == "updated"
    assert group["column"] == "review"


def test_startup_resumes_ready_initialization_and_repairs_agent_column(tmp_path):
    class FakeCodexTasks:
        def register_group(self, group, inventory, thread_id=None):
            raise AssertionError("Startup must not launch Codex")

    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    inventory = GroupInventoryStore(store.path)
    store.add_manual_group("ready", "catalog")
    inventory.replace(GroupInventorySnapshot(
        group_key="ready", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="10",
        items=(GroupInventoryItem("parent", "10", 0, True, True, True),),
    ))
    store.add_manual_group("blocked", "catalog")
    store.update_group("blocked", {"column": "work", "agent_status": "blocked"})
    with store.connect() as connection:
        connection.execute("UPDATE groups SET manual_column = 'work' WHERE group_key = 'blocked'")

    _resume_automatic_groups(store, inventory, FakeCodexTasks())

    assert store.get_group("ready")["agent_status"] is None
    assert store.get_group("ready")["column"] == "queue"
    assert store.get_group("ready")["codex_thread_id"] is None
    assert store.get_group("blocked")["column"] == "issues"


def test_group_api_lists_updates_and_comments(tmp_path):
    class FakeInitializer:
        def __init__(self):
            self.started = []

        def start(self, group_key):
            self.started.append(group_key)
            return {"group_id": group_key, "status": "pending", "total": 0}

        def get(self, group_key):
            return {"group_id": group_key, "status": "running", "total": 0}

    class FakeCodexTasks:
        def __init__(self):
            self.comments = []

        def send_comment(self, thread_id, group, body):
            self.comments.append((thread_id, body))

    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.upsert_fact({
        "group_key": "123", "title": "Тема", "path": "Тема", "source": "Каталог",
        "source_id": "catalog", "registered": 1, "legacy": 0, "workflow": "content_rule",
        "handler": "test", "total": 2, "transformed": 0, "helpers": 0, "errors": 0,
        "blocked": 0, "latest_run": None, "run_status": None, "system_column": "work",
        "synced_at": "now",
    })
    initializer = FakeInitializer()
    codex_tasks = FakeCodexTasks()
    store.update_group("123", {"codex_thread_id": "thread-123", "task_title": "Регистрация 123"})
    profile = SimpleNamespace(
        catalog_snapshot_id="4073fc7b-2056-4697-b18b-38741c94d0f4",
        snapshot_theme_id="theme-uuid",
        source_group_id="group-uuid",
        category_key="1",
    )
    server = make_server(store=store, var_dir=tmp_path / "var", profiles={"123": profile}, static_dir=tmp_path, initializer=initializer, codex_tasks=codex_tasks, port=0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        _, created = _request(
            f"{base}/api/groups",
            method="POST",
            payload={
                "id": "  Группа 506803  ",
                "catalog_id": "41bc4d03-40cd-4407-8dea-df76e3f47ea8",
                "note": "Проверить картинку условия",
                "agent_sample_size": 2,
            },
        )
        assert created["column"] == "initialization"
        assert created["source_id"] == "41bc4d03-40cd-4407-8dea-df76e3f47ea8"
        assert created["agent_sample_size"] == 2
        assert created["id"] == "506803"
        assert initializer.started == ["506803"]
        assert store.list_comments("506803")[0]["body"] == "Проверить картинку условия"
        status, initialization = _request(f"{base}/api/groups/506803/initialization")
        assert status == 200
        assert initialization["status"] == "running"
        status, groups = _request(f"{base}/api/groups")
        assert status == 200
        assert {group["id"] for group in groups["groups"]} == {"123", "506803"}
        assert {item["name"] for item in groups["catalogs"]} >= {
            "Каталог ОГЭ МАТ", "Каталог ЕГЭ МАТ БАЗА", "Каталог ЕГЭ МАТ ПРОФИЛЬ",
        }
        registered = next(group for group in groups["groups"] if group["id"] == "123")
        assert registered.get("teacherhelper") == {
            "source_site_id": "7bed2492-5b8b-4c88-9be8-7d47916cd7c6",
            "snapshot_id": "4073fc7b-2056-4697-b18b-38741c94d0f4",
            "category_id": "c226053c-29e7-4e88-aafb-81896ab0d969",
            "theme_id": "theme-uuid",
            "group_id": "group-uuid",
        }
        _, registered_detail = _request(f"{base}/api/groups/123")
        assert registered_detail["teacherhelper"] == registered["teacherhelper"]

        _, group = _request(f"{base}/api/groups/123", method="PATCH", payload={"column": "review"})
        assert group["column"] == "review"

        _, result = _request(f"{base}/api/groups/123/comments", method="POST", payload={"body": "Проверить превью"})
        assert result["comment"]["body"] == "Проверить превью"
        assert result["group"]["column"] == "work"
        assert codex_tasks.comments == [("thread-123", "Проверить превью")]
        _, comments = _request(f"{base}/api/groups/123/comments")
        assert [item["body"] for item in comments["comments"]] == ["Проверить превью"]

        save_preview(tmp_path / "var/dashboard/previews", {
            "group_key": "123",
            "parent": {"source_problem_id": "10"},
            "result": {"source_problem_id": "11"},
        })
        status, preview = _request(f"{base}/api/groups/123/preview")
        assert status == 200
        assert preview["result"]["source_problem_id"] == "11"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_group_api_registers_with_selected_or_new_codex_task(tmp_path):
    class FakeCodexTasks:
        def __init__(self):
            self.registrations = []
            self.comments = []

        def list_tasks(self):
            return [{"id": "thread-existing", "title": "Existing task", "model": "gpt-5.6-terra", "reasoning_effort": "medium"}]

        def register_group(self, group, inventory, thread_id=None, comment=""):
            self.registrations.append((group["id"], inventory["parent_problem_id"], thread_id, comment))
            task_id = thread_id or "thread-new"
            return {"id": task_id, "title": "Existing task" if thread_id else "Регистрация группы 123"}

        def send_comment(self, thread_id, group, body, source_problem_id=None):
            self.comments.append((thread_id, group["id"], body, source_problem_id))

    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")
    store.update_group("123", {"column": "issues"})
    inventory = GroupInventoryStore(store.path)
    inventory.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="10",
        items=(GroupInventoryItem("parent", "10", 0, True, True, True),),
    ))
    codex_tasks = FakeCodexTasks()
    server = make_server(
        store=store, inventory_store=inventory, codex_tasks=codex_tasks,
        var_dir=tmp_path / "var", profiles={}, static_dir=tmp_path, port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        _, tasks = _request(f"{base}/api/codex/tasks")
        assert tasks["tasks"][0]["id"] == "thread-existing"

        _, result = _request(
            f"{base}/api/groups/123/register", method="POST",
            payload={"thread_id": "thread-existing", "comment": "Проверь задачу 42"},
        )
        assert result["group"]["codex_thread_id"] == "thread-existing"
        assert result["group"]["column"] == "work"
        assert codex_tasks.registrations == [("123", "parent", "thread-existing", "Проверь задачу 42")]

        store.update_group("123", {"column": "issues"})
        _, comment = _request(
            f"{base}/api/groups/123/comments", method="POST",
            payload={"body": "Исправь выбор рисунка"},
        )
        assert comment["group"]["column"] == "work"
        assert codex_tasks.comments == [("thread-existing", "123", "Исправь выбор рисунка", None)]

        _, work_comment = _request(
            f"{base}/api/groups/123/comments", method="POST",
            payload={"body": "Проверь результат ещё раз"},
        )
        assert work_comment["group"]["agent_status"] == "working"
        assert codex_tasks.comments[-1] == (
            "thread-existing", "123", "Проверь результат ещё раз", None,
        )

        _, task_comment = _request(
            f"{base}/api/groups/123/comments", method="POST",
            payload={"body": "Проверь формулировку", "problem_id": "parent"},
        )
        assert task_comment["comment"]["problem_id"] == "parent"
        assert codex_tasks.comments[-1] == ("thread-existing", "123", "Проверь формулировку", "10")

        store.update_group("123", {"agent_status": "blocked"})
        with store.connect() as connection:
            connection.execute("UPDATE groups SET manual_column = 'work' WHERE group_key = '123'")
        _, restarted = _request(
            f"{base}/api/groups/123/comments", method="POST",
            payload={"body": "Повторный запуск после блокировки"},
        )
        assert restarted["group"]["agent_status"] == "working"
        assert codex_tasks.comments[-1] == (
            "thread-existing", "123", "Повторный запуск после блокировки", None,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_done_group_can_archive_its_codex_task(tmp_path):
    class FakeCodexTasks:
        def __init__(self):
            self.archived = []

        def archive_task(self, thread_id):
            self.archived.append(thread_id)

    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")
    store.update_group("123", {
        "column": "done",
        "codex_thread_id": "thread-123",
        "task_url": "codex://threads/thread-123",
    })
    codex_tasks = FakeCodexTasks()
    server = make_server(
        store=store, codex_tasks=codex_tasks,
        var_dir=tmp_path / "var", profiles={}, static_dir=tmp_path, port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        _, result = _request(
            f"http://127.0.0.1:{server.server_port}/api/groups/123/archive-codex",
            method="POST",
        )
        assert codex_tasks.archived == ["thread-123"]
        assert result["group"]["codex_archived"] is True
        assert result["group"]["task_url"] == "codex://threads/thread-123"
        _, repeated = _request(
            f"http://127.0.0.1:{server.server_port}/api/groups/123/archive-codex",
            method="POST",
        )
        assert repeated["group"]["codex_archived"] is True
        assert codex_tasks.archived == ["thread-123"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_group_api_starts_and_reads_local_dry_run(tmp_path):
    class FakeDryRuns:
        def __init__(self):
            self.started = []

        def start(self, group_key, mode):
            self.started.append((group_key, mode))
            return {"group_key": group_key, "mode": mode, "status": "queued"}

        def get(self, group_key):
            return {"group_key": group_key, "mode": "parent", "status": "running"}

        def start_additional(self, group_key):
            self.started.append((group_key, "additional"))
            return {"group_key": group_key, "mode": "random", "status": "queued", "append": True}

        def start_problem(self, group_key, problem_id):
            self.started.append((group_key, "problem", problem_id))
            return {"group_key": group_key, "mode": "problem", "status": "queued", "selected_problem_id": problem_id}

    class FakeApplies:
        def __init__(self):
            self.started = []

        def start(self, group_key, problem_id):
            self.started.append((group_key, problem_id))
            return {"group_key": group_key, "problem_id": problem_id, "status": "queued"}

        def start_group(self, group_key):
            self.started.append((group_key, "group"))
            return {"group_key": group_key, "scope": "group", "status": "queued"}

        def start_helpers(self, group_key, problem_id=None):
            self.started.append((group_key, "helpers", problem_id))
            return {"group_key": group_key, "scope": "problem" if problem_id else "group", "stage": "helpers", "status": "queued"}

        def get(self, group_key):
            return {"group_key": group_key, "problem_id": "child", "status": "running"}

    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")
    dry_runs = FakeDryRuns()
    applies = FakeApplies()
    server = make_server(
        store=store,
        var_dir=tmp_path / "var",
        profiles={"123": object()},
        static_dir=tmp_path,
        dry_runs=dry_runs,
        applies=applies,
        port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        status, queued = _request(
            f"{base}/api/groups/123/dry-run",
            method="POST",
            payload={"mode": "parent"},
        )
        assert status == 202
        assert queued["status"] == "queued"
        assert dry_runs.started == [("123", "parent")]

        status, queued = _request(
            f"{base}/api/groups/123/preview",
            method="POST",
            payload={},
        )
        assert status == 202
        assert queued["append"] is True
        assert dry_runs.started[-1] == ("123", "additional")

        status, queued = _request(
            f"{base}/api/groups/123/dry-run",
            method="POST",
            payload={"mode": "problem", "problem_id": "child"},
        )
        assert status == 202
        assert queued["selected_problem_id"] == "child"
        assert dry_runs.started[-1] == ("123", "problem", "child")

        status, running = _request(f"{base}/api/groups/123/dry-run")
        assert status == 200
        assert running["status"] == "running"

        status, queued = _request(
            f"{base}/api/groups/123/apply",
            method="POST",
            payload={"problem_id": "child"},
        )
        assert status == 202
        assert queued["problem_id"] == "child"
        assert applies.started == [("123", "child")]

        status, queued = _request(
            f"{base}/api/groups/123/apply",
            method="POST",
            payload={"scope": "group"},
        )
        assert status == 202
        assert queued["scope"] == "group"
        assert applies.started[-1] == ("123", "group")

        status, queued = _request(
            f"{base}/api/groups/123/apply",
            method="POST",
            payload={"stage": "helpers", "problem_id": "child"},
        )
        assert status == 202
        assert queued["stage"] == "helpers"
        assert applies.started[-1] == ("123", "helpers", "child")

        status, queued = _request(
            f"{base}/api/groups/123/apply",
            method="POST",
            payload={"stage": "helpers", "scope": "group"},
        )
        assert status == 202
        assert queued["scope"] == "group"
        assert applies.started[-1] == ("123", "helpers", None)

        status, applying = _request(f"{base}/api/groups/123/apply")
        assert status == 200
        assert applying["status"] == "running"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_group_api_projects_active_runner_job_into_separate_queue_column(tmp_path):
    class FakeDryRuns:
        def get(self, group_key):
            assert group_key == "123"
            return {"group_key": group_key, "mode": "all", "status": "queued"}

    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")
    server = make_server(
        store=store,
        var_dir=tmp_path / "var",
        profiles={},
        static_dir=tmp_path,
        dry_runs=FakeDryRuns(),
        port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, payload = _request(f"http://127.0.0.1:{server.server_port}/api/groups")
        assert status == 200
        group = payload["groups"][0]
        assert group["column"] == "jobs"
        assert group["job"] == {"kind": "dry_run", "status": "queued", "scope": "group"}
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_group_api_lists_initialized_tasks(tmp_path):
    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")
    inventory = GroupInventoryStore(store.path)
    inventory.replace(GroupInventorySnapshot(
        group_key="123",
        catalog_snapshot_id="catalog",
        source_group_id="source-group",
        parent_problem_id="parent",
        parent_source_problem_id="10",
        items=(GroupInventoryItem("parent", "10", 0, True, True, True),),
    ))
    server = make_server(
        store=store,
        inventory_store=inventory,
        var_dir=tmp_path / "var",
        profiles={},
        static_dir=tmp_path,
        port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, payload = _request(
            f"http://127.0.0.1:{server.server_port}/api/groups/123/tasks"
        )
        assert status == 200
        assert payload["parent_problem_id"] == "parent"
        assert payload["tasks"][0]["source_problem_id"] == "10"
        assert payload["tasks"][0]["has_solution"] == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_group_api_reads_normalized_preview_for_one_indexed_problem(tmp_path):
    class Gateway:
        def get_problem_pipeline_state(self, problem_id):
            return {"statuses": {"normalized": "ready"}}

        def get_problem_context(self, problem_id):
            return {"normalized_content": {
                "sections": [{"key": "condition", "html": "<p>Условие</p>"}],
                "assets": [],
            }}

        def close(self):
            pass

    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")
    inventory = GroupInventoryStore(store.path)
    inventory.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="problem", parent_source_problem_id="42",
        items=(GroupInventoryItem("problem", "42", 0, True, False, False),),
    ))
    server = make_server(
        store=store, inventory_store=inventory, var_dir=tmp_path / "var",
        profiles={}, static_dir=tmp_path, preview_gateway_factory=Gateway, port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, payload = _request(
            f"http://127.0.0.1:{server.server_port}/api/groups/123/tasks/problem/preview"
        )
        assert status == 200
        assert payload["samples"][0]["before"]["condition_html"] == "<p>Условие</p>"
        assert payload["samples"][0]["after"] is None
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_group_api_rejects_one_indexed_problem_and_returns_updated_group(tmp_path):
    class Gateway:
        def reject_problem_content_pipeline(self, problem_id, reason):
            return {"problem_id": problem_id, "reason": reason}

        def get_problem_pipeline_state(self, problem_id):
            return {"statuses": {"normalized": "rejected"}}

        def close(self):
            pass

    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")
    inventory = GroupInventoryStore(store.path)
    inventory.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="1",
        items=(
            GroupInventoryItem("parent", "1", 0, True, True, True),
            GroupInventoryItem("bad", "2", 1, True, False, True),
        ),
    ))
    server = make_server(
        store=store, inventory_store=inventory, var_dir=tmp_path / "var",
        profiles={}, static_dir=tmp_path, preview_gateway_factory=Gateway, port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, payload = _request(
            f"http://127.0.0.1:{server.server_port}/api/groups/123/tasks/bad/reject",
            method="POST",
            payload={"reason": "Некорректное условие"},
        )
        assert status == 200
        assert payload["rejection"]["status"] == "rejected"
        assert [item["problem_id"] for item in inventory.list_items("123")] == ["parent"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_group_api_exposes_saved_activity(tmp_path):
    store = DashboardStore(tmp_path / "dashboard.sqlite3")
    store.add_manual_group("123", "catalog")
    inventory = GroupInventoryStore(store.path)
    inventory.replace(GroupInventorySnapshot(
        group_key="123", catalog_snapshot_id="catalog", source_group_id="source-group",
        parent_problem_id="parent", parent_source_problem_id="10",
        items=(GroupInventoryItem("parent", "10", 0, True, True, True),),
    ))
    run = tmp_path / "var/runs/20260907T000000Z-group-123"
    run.mkdir(parents=True)
    (run / "summary.json").write_text(json.dumps({
        "group_key": "123", "status": "completed", "targets": 1, "apply": True,
    }))
    server = make_server(
        store=store, inventory_store=inventory, var_dir=tmp_path / "var",
        profiles={}, static_dir=tmp_path, port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, payload = _request(
            f"http://127.0.0.1:{server.server_port}/api/groups/123/activity"
        )
        assert status == 200
        assert payload["latest"]["kind"] == "apply"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
