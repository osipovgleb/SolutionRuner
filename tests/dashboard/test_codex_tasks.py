from solution_runner.dashboard.codex_tasks import (
    CodexTaskService,
    build_registration_prompt,
)


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
    created = service.register_group(group, inventory)

    assert existing["id"] == "thread-1"
    assert existing["title"] == "Existing"
    assert calls[0][0:2] == ("send", "thread-1")
    assert created["id"] == "thread-new"
    assert created["title"] == "123 · Уравнения"
    assert calls[1][0:3] == ("create", "gpt-5.6-terra", "medium")
