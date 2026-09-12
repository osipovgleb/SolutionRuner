from subprocess import CompletedProcess
from threading import Event

from solution_runner.dashboard.codex_tasks import (
    AUTOMATION_ACCESS_ARGS,
    CodexTaskService,
    _SerialMessageSender,
    _list_threads,
    _send_message,
    build_registration_prompt,
)


def test_automatic_tasks_get_full_access_without_teacherhelper_prompts():
    joined = " ".join(AUTOMATION_ACCESS_ARGS)
    assert 'sandbox_mode="danger-full-access"' in joined
    assert 'approval_policy="never"' in joined
    assert 'mcp_servers.teacherhelper.default_tools_approval_mode="approve"' in joined
    assert 'mcp_servers.teacherhelper_org.default_tools_approval_mode="approve"' in joined


def test_registration_prompt_defines_the_bounded_registration_job():
    prompt = build_registration_prompt(
        {"id": "123", "title": "Уравнения", "source_id": "catalog"},
        {"parent_problem_id": "parent", "parent_source_problem_id": "10", "task_count": 17},
    )

    assert "SQLite" in prompt
    assert "родител" in prompt
    assert "соседн" in prompt
    assert "существующ" in prompt and "раннер" in prompt
    assert "group_item_stage_results" in prompt
    assert "source_problem_id" in prompt
    assert "superpowers" in prompt
    assert "agent_status" in prompt
    assert "agent_summary" in prompt
    assert "полный локальный dry-run всей группы" in prompt.lower()
    assert "needs_input" in prompt
    assert "full_dry_run_status='ready'" in prompt
    assert "не выполняй apply" in prompt.lower()


def test_registration_prompt_appends_the_user_comment():
    prompt = build_registration_prompt(
        {"id": "123", "title": "Уравнения", "source_id": "catalog"},
        {"parent_problem_id": "parent", "parent_source_problem_id": "10", "task_count": 17},
        "  Проверь отдельно задачу 42.  ",
    )

    assert prompt.endswith("Комментарий пользователя:\nПроверь отдельно задачу 42.")


def test_service_selects_existing_task_or_creates_terra_medium(tmp_path):
    calls = []
    tasks = [{"id": "thread-1", "title": "Existing", "model": "gpt-5.6-terra", "reasoningEffort": "medium"}]
    service = CodexTaskService(
        project_root=tmp_path,
        list_threads=lambda: tasks,
        create_thread=lambda prompt, model, effort: calls.append(("create", model, effort, prompt)) or "thread-new",
        send_message=lambda thread_id, prompt: calls.append(("send", thread_id, prompt)),
    )
    group = {"id": "123", "title": "Уравнения", "source_id": "catalog"}
    inventory = {"parent_problem_id": "parent", "parent_source_problem_id": "10", "task_count": 17}

    existing = service.register_group(group, inventory, "thread-1")
    created = service.register_group(group, inventory, comment="Проверь задачу 42")

    assert existing["id"] == "thread-1"
    assert existing["title"] == "Existing"
    assert calls[0][0:2] == ("send", "thread-1")
    assert created["id"] == "thread-new"
    assert created["title"] == "123 · Уравнения"
    assert calls[1][0:3] == ("create", "gpt-5.6-terra", "medium")
    assert calls[1][3].endswith("Комментарий пользователя:\nПроверь задачу 42")


def test_task_without_title_uses_only_first_preview_line(tmp_path):
    service = CodexTaskService(
        project_root=tmp_path,
        list_threads=lambda: [{"id": "thread-1", "title": None, "preview": "315122 · Окружность\n\nДлинный промпт"}],
    )

    assert service.list_tasks()[0]["title"] == "315122 · Окружность"


def test_comment_is_sent_with_short_group_tag(tmp_path):
    sent = []
    service = CodexTaskService(project_root=tmp_path, send_message=lambda thread_id, prompt: sent.append((thread_id, prompt)))

    service.send_comment("thread-1", {"id": "315122", "title": "Окружность"}, "helpers у всех готово?")

    assert sent == [("thread-1", "Группа 315122: helpers у всех готово?")]

    service.send_comment(
        "thread-1",
        {"id": "315122", "title": "Окружность"},
        "перепроверь решение",
        "509640",
    )
    assert sent[-1] == ("thread-1", "Группа 315122 · задача 509640: перепроверь решение")


def test_service_archives_task(tmp_path):
    archived = []
    service = CodexTaskService(project_root=tmp_path, archive_thread=archived.append)

    service.archive_task("thread-1")

    assert archived == ["thread-1"]


def test_messages_for_one_task_run_in_submission_order():
    first_started = Event()
    release_first = Event()
    second_finished = Event()
    calls = []

    def send(_thread_id, prompt):
        calls.append(f"start:{prompt}")
        if prompt == "first":
            first_started.set()
            release_first.wait(timeout=1)
        calls.append(f"finish:{prompt}")
        if prompt == "second":
            second_finished.set()

    sender = _SerialMessageSender(send)
    sender("thread", "first")
    assert first_started.wait(timeout=1)
    sender("thread", "second")
    assert not second_finished.wait(timeout=0.05)
    release_first.set()
    assert second_finished.wait(timeout=1)
    assert calls == ["start:first", "finish:first", "start:second", "finish:second"]


def test_send_message_queues_into_app_owned_task(monkeypatch, tmp_path):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return CompletedProcess(command, 0)

    monkeypatch.setattr("solution_runner.dashboard.codex_tasks.subprocess.run", run)
    exits = []

    _send_message(tmp_path, "thread-1", "hello", lambda thread_id, code: exits.append((thread_id, code)))

    assert calls[0][0] == [
        "codex", "queue", "--thread", "thread-1", "--message", "hello",
        *AUTOMATION_ACCESS_ARGS,
        "-C", str(tmp_path),
    ]
    assert exits == []


def test_list_threads_includes_all_regular_sources_and_pages(monkeypatch, tmp_path):
    calls = []

    def request(_root, method, params):
        calls.append((method, params))
        if params.get("cursor") is None:
            return {"data": [{"id": "first"}], "nextCursor": "page-2"}
        return {"data": [{"id": "second"}], "nextCursor": None}

    monkeypatch.setattr("solution_runner.dashboard.codex_tasks._app_server_request", request)

    assert [item["id"] for item in _list_threads(tmp_path)] == ["first", "second"]
    assert calls[0][1]["sourceKinds"] == ["cli", "vscode", "exec", "appServer", "unknown"]
    assert calls[1][1]["cursor"] == "page-2"
