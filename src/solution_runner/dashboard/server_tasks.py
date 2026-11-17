"""Coordinate dashboard group tasks and their completion states."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from solution_runner.group_inventory_store import GroupInventoryStore

from .codex_tasks import CodexTaskService, CodexTaskStartError
from .store import DashboardStore


def _register_group_task(
    store: DashboardStore,
    inventory_store: GroupInventoryStore,
    codex_tasks: CodexTaskService,
    group_key: str,
    thread_id: str | None = None,
    comment: str = "",
) -> tuple[dict[str, str], dict[str, Any]]:
    group = store.get_group(group_key)
    snapshot = inventory_store.get(group_key)
    if group is None or snapshot is None:
        raise KeyError(group_key)
    inventory = {
        "parent_problem_id": snapshot.parent_problem_id,
        "parent_source_problem_id": snapshot.parent_source_problem_id,
        "task_count": len(inventory_store.list_items(group_key)),
    }
    thread_id = thread_id or group.get("codex_thread_id")

    def bind_created_task(created_id: str) -> None:
        # Bind before the first turn can finish, so lifecycle callbacks find the card.
        store.update_group(
            group_key,
            {
                "codex_thread_id": created_id,
                "task_title": f"{group_key} · {group['title']}",
                "task_url": f"codex://threads/{created_id}",
                "agent_status": "working",
                "column": "work",
                "full_dry_run_status": None,
            },
        )

    try:
        task = codex_tasks.register_group(
            group, inventory, thread_id, comment, on_created=bind_created_task
        )
    except CodexTaskStartError as exc:
        store.update_group(
            group_key,
            {
                "codex_thread_id": exc.thread_id,
                "task_title": f"{group_key} · {group['title']}",
                "task_url": f"codex://threads/{exc.thread_id}",
                "agent_status": "blocked",
                "agent_summary": str(exc)[:200],
            },
        )
        raise
    # Preserve a terminal state if a fast first turn already completed.
    current = store.get_group(group_key) or {}
    completed_early = current.get("codex_thread_id") == task["id"] and current.get(
        "agent_status"
    ) in {"updated", "no_changes", "blocked", "needs_input", "verifying"}
    updated = store.update_group(
        group_key,
        {
            "codex_thread_id": task["id"],
            "codex_archived": 0,
            "task_title": task["title"],
            "task_url": f"codex://threads/{task['id']}",
            "column": current.get("column", "work") if completed_early else "work",
            "revision_requested": 0,
            "full_dry_run_status": current.get("full_dry_run_status")
            if completed_early
            else None,
            "agent_status": current.get("agent_status")
            if completed_early
            else "working",
            "agent_summary": current.get("agent_summary")
            if completed_early
            else "Агент исследует группу и готовит полный dry-run.",
        },
    )
    assert updated is not None
    return task, updated


def _handle_codex_exit(
    store: DashboardStore,
    thread_id: str,
    return_code: int,
    dry_runs: Any | None = None,
) -> bool:
    group = next(
        (
            item
            for item in store.list_groups()
            if item.get("codex_thread_id") == thread_id
        ),
        None,
    )
    if not group:
        return False
    if group.get("agent_status") in {"updated", "no_changes"}:
        if group.get("full_dry_run_status") == "ready":
            return group.get("agent_status") == "updated"
        if dry_runs is None:
            store.update_group(
                str(group["id"]),
                {
                    "agent_status": "blocked",
                    "agent_summary": "Результат агента не подтверждён полным dry-run.",
                },
            )
            return False
        store.update_group(
            str(group["id"]),
            {
                "agent_status": "verifying",
                "full_dry_run_status": "running",
                "agent_summary": "Сервер проверяет результат полным dry-run.",
            },
        )
        try:
            dry_runs.start(str(group["id"]), "all")
        except (KeyError, ValueError, RuntimeError) as exc:
            store.update_group(
                str(group["id"]),
                {
                    "agent_status": "blocked",
                    "full_dry_run_status": "failed",
                    "agent_summary": f"Полный dry-run не запущен: {' '.join(str(exc).split())}"[
                        :200
                    ],
                },
            )
        return False
    if group.get("agent_status") != "working":
        return False
    store.update_group(
        str(group["id"]),
        {
            "agent_status": "blocked" if return_code else "needs_input",
            "agent_summary": (
                f"Codex завершился с кодом {return_code}; открой задачу и повтори запуск."
                if return_code
                else "Codex остановился без итогового статуса; открой задачу — возможно, нужен ответ."
            ),
        },
    )
    return False


def _finish_initialization(
    store: DashboardStore,
    inventory_store: GroupInventoryStore,
    codex_tasks: CodexTaskService,
    group_key: str,
    state: Mapping[str, Any],
) -> None:
    if state.get("status") != "ready":
        store.update_group(
            group_key,
            {
                "agent_status": "blocked",
                "agent_summary": f"Инициализация не завершена: {state.get('error') or 'неизвестная ошибка'}"[
                    :200
                ],
            },
        )
        return
    store.update_group(
        group_key,
        {
            "column": "queue",
            "agent_status": None,
            "agent_summary": "Инициализация завершена. Группа готова к ручной регистрации из проекта.",
        },
    )


def _finish_automatic_dry_run(
    store: DashboardStore,
    group_key: str,
    state: Mapping[str, Any],
) -> None:
    group = store.get_group(group_key)
    if (
        not group
        or group.get("agent_status") != "verifying"
        or state.get("mode") != "all"
    ):
        return
    completed = state.get("status") == "completed"
    store.update_group(
        group_key,
        {
            "agent_status": "updated" if completed else "blocked",
            "agent_summary": (
                "Полный dry-run завершён успешно."
                if completed
                else f"Полный dry-run не прошёл: {state.get('error') or state.get('status')}"
            )[:200],
        },
    )


def _resume_automatic_groups(
    store: DashboardStore,
    inventory_store: GroupInventoryStore,
    codex_tasks: CodexTaskService,
) -> None:
    for group in store.list_groups():
        group_key = str(group["id"])
        if group.get("agent_status"):
            store.update_group(group_key, {"agent_status": group["agent_status"]})
        snapshot = inventory_store.get(group_key)
        if (
            group.get("column") == "initialization"
            and snapshot is not None
            and snapshot.status == "ready"
            and not group.get("codex_thread_id")
        ):
            _finish_initialization(
                store, inventory_store, codex_tasks, group_key, {"status": "ready"}
            )
