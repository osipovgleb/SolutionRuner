"""Connect dashboard groups to real local Codex tasks."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any, Callable, Mapping

from .codex_transport import shared_client


MODEL = "gpt-6.1-sol"
EFFORT = "medium"


def build_registration_prompt(
    group: Mapping[str, Any],
    inventory: Mapping[str, Any],
    comment: str = "",
) -> str:
    """Build the bounded, repeatable prompt used for group registration."""

    prompt = f"""{group['id']} · {group['title']}

Зарегистрируй группу SolutionRunner {group['id']} — «{group['title']}».

Источник истины — локальный SQLite-индекс дэшборда `var/dashboard/dashboard.sqlite3`. Не используй старые manifest-файлы как реестр.
В группе {inventory['task_count']} задач; родитель: локальный ID {inventory['parent_problem_id']}, source ID {inventory['parent_source_problem_id']}.

Сначала найди в SQLite все незакрытые проблемы именно этой группы: соедини `group_item_stage_results` и `group_inventory_items` по `group_key` и `problem_id`; изучи `dry_run_error`, `apply_error`, `error` и статусы Apply/Helpers. Для каждой причины зафиксируй внешний `source_problem_id` и объясни, какой этап раннера её вызвал. Не останавливайся на том, что профиль уже зарегистрирован: если есть хотя бы одна проблема, сначала исследуй её карточку и только затем решай, нужна ли правка.

Затем изучи проблемные задачи через TeacherHelper MCP, соседние зарегистрированные группы и существующие раннеры. Подбери наиболее близкий раннер: переиспользуй или минимально адаптируй его; создавай новый только если подходящего действительно нет.

Если без ответа пользователя нельзя выбрать корректное поведение, до вопроса обнови карточку: `agent_status='needs_input'`, а в `agent_summary` запиши сам вопрос до 200 символов. Затем задай тот же вопрос в задаче Codex и остановись.

После исследования и изменений обязательно запусти полный локальный dry-run всей группы без внешней записи. Если он выявил исправимую ошибку, исследуй её, исправь и повтори полный dry-run; не останавливайся после первой неудачи. Не выполняй Apply, Helpers или Reject через MCP. Не используй навыки `superpowers`. Не коммить и не пушь изменения.

Перед финальным сообщением обязательно обнови карточку этой группы в SQLite через `DashboardStore(...).update_group(...)`. Только после успешного полного dry-run выставь `agent_status` в `updated` или `no_changes` и `full_dry_run_status='ready'`. Если dry-run не прошёл или работа заблокирована, выставь `agent_status='blocked'` и `full_dry_run_status='failed'`. В `agent_summary` запиши короткий итог до 200 символов с проблемным `source_problem_id` и результатом. Карточка — обязательный итог работы, а не только сообщение в треде."""
    comment = comment.strip()
    return prompt if not comment else f"{prompt}\n\nКомментарий пользователя:\n{comment}"



def _app_server_request(project_root: Path, method: str, params: Mapping[str, Any]) -> dict[str, Any]:
    return shared_client(project_root).request(method, dict(params))


def _list_threads(project_root: Path) -> list[dict[str, Any]]:
    threads = []
    cursor = None
    while True:
        result = _app_server_request(project_root, "thread/list", {
            "cwd": str(project_root),
            "limit": 100,
            "archived": False,
            "sourceKinds": ["cli", "vscode", "exec", "appServer", "unknown"],
            "cursor": cursor,
        })
        threads.extend(item for item in result.get("data", []) if isinstance(item, dict))
        cursor = result.get("nextCursor")
        if not cursor:
            return threads


def _archive_thread(project_root: Path, thread_id: str) -> None:
    _app_server_request(project_root, "thread/archive", {"threadId": thread_id})


def _create_thread(
    project_root: Path,
    prompt: str,
    model: str,
    effort: str,
    on_exit: Callable[[str, int], None] | None = None,
    on_created: Callable[[str], None] | None = None,
) -> str:
    """Create and start one durable task in the shared daemon through T3 transport."""
    client = shared_client(project_root)
    result = client.request("thread/start", {
        "cwd": str(project_root), "model": model,
        "approvalPolicy": "never", "sandbox": "danger-full-access",
        "config": {
            "model_reasoning_effort": effort,
            "mcp_servers.teacherhelper.default_tools_approval_mode": "approve",
            "mcp_servers.teacherhelper_org.default_tools_approval_mode": "approve",
        },
        "threadSource": "appServer", "ephemeral": False,
    })
    thread_id = str((result.get("thread") or {}).get("id") or "")
    if not thread_id:
        raise RuntimeError("Codex did not create a task")
    try:
        client.request("thread/name/set", {"threadId": thread_id, "name": prompt.splitlines()[0]})
        if on_created:
            on_created(thread_id)
        turn_id = client.start_turn(thread_id, prompt, model, effort)
    except RuntimeError as exc:
        raise CodexTaskStartError(thread_id, str(exc)) from exc
    Thread(target=_watch_turn, args=(client, thread_id, turn_id, on_exit), daemon=True).start()
    return thread_id


class CodexTaskStartError(RuntimeError):
    """Retain a created task ID even when admitting its first turn fails."""

    def __init__(self, thread_id: str, message: str):
        super().__init__(message)
        self.thread_id = thread_id


def _watch_turn(client, thread_id, turn_id, on_exit):
    try:
        code = client.wait_turn(turn_id)
    except RuntimeError:
        code = 1
    if on_exit:
        on_exit(thread_id, code)


def _send_message(
    project_root: Path, thread_id: str, prompt: str,
) -> None:
    """Queue at the task's existing owner instead of acquiring a second writer."""
    try:
        result = subprocess.run(
            ['codex', 'queue', '--thread', thread_id, '--message', prompt],
            cwd=project_root, capture_output=True, text=True, timeout=20, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError(f'Не удалось передать сообщение владельцу чата Codex: {exc}') from exc
    if result.returncode:
        reason = (result.stderr or result.stdout).strip()[-500:]
        raise RuntimeError(f'Сообщение не доставлено в Codex App: {reason or result.returncode}')


class _SerialMessageSender:
    """Serialize queue admission and return real delivery errors to the HTTP caller."""

    def __init__(self, send: Callable[[str, str], None]) -> None:
        self._send = send
        self._lock = Lock()
        self._tails: dict[str, Event] = {}

    def __call__(self, thread_id: str, prompt: str) -> None:
        done = Event()
        with self._lock:
            previous = self._tails.get(thread_id)
            self._tails[thread_id] = done
        if previous:
            previous.wait()
        try:
            self._send(thread_id, prompt)
        finally:
            done.set()
            with self._lock:
                if self._tails.get(thread_id) is done:
                    self._tails.pop(thread_id, None)


class CodexTaskService:
    def __init__(
        self,
        *,
        project_root: Path,
        list_threads: Callable[[], list[dict[str, Any]]] | None = None,
        create_thread: Callable[[str, str, str], str] | None = None,
        send_message: Callable[[str, str], None] | None = None,
        archive_thread: Callable[[str], None] | None = None,
        on_exit: Callable[[str, int], None] | None = None,
    ) -> None:
        self.project_root = project_root
        self._list = list_threads or (lambda: _list_threads(project_root))
        self._custom_create = create_thread
        self._on_exit = on_exit
        self._send = send_message or _SerialMessageSender(
            lambda thread_id, prompt: _send_message(project_root, thread_id, prompt)
        )
        self._archive = archive_thread or (lambda thread_id: _archive_thread(project_root, thread_id))

    def list_tasks(self) -> list[dict[str, Any]]:
        return [{
            "id": str(item["id"]),
            "title": str(item.get("name") or item.get("title") or str(item.get("preview") or item["id"]).splitlines()[0]),
            "model": item.get("model"),
            "reasoning_effort": item.get("reasoningEffort"),
            "status": item.get("status"),
            "updated_at": item.get("updatedAt"),
        } for item in self._list() if item.get("id")]

    def register_group(
        self,
        group: Mapping[str, Any],
        inventory: Mapping[str, Any],
        thread_id: str | None = None,
        comment: str = "",
        on_created: Callable[[str], None] | None = None,
    ) -> dict[str, str]:
        prompt = build_registration_prompt(group, inventory, comment)
        if thread_id:
            task = next((item for item in self.list_tasks() if item["id"] == thread_id), None)
            if task is None:
                raise ValueError("selected Codex task does not exist in this project")
            if on_created:
                on_created(thread_id)
            self._send(thread_id, prompt)
            return {"id": thread_id, "title": str(task["title"])}
        model = os.environ.get("SOLUTION_RUNNER_CODEX_MODEL", MODEL)
        effort = os.environ.get("SOLUTION_RUNNER_CODEX_EFFORT", EFFORT)
        if self._custom_create:
            created_id = self._custom_create(prompt, model, effort)
            if on_created:
                on_created(created_id)
        else:
            created_id = _create_thread(self.project_root, prompt, model, effort, self._on_exit, on_created)
        return {"id": created_id, "title": f"{group['id']} · {group['title']}"}

    def send_comment(self, thread_id: str, group: Mapping[str, Any], body: str, source_problem_id: str | None = None) -> None:
        target = f" · задача {source_problem_id}" if source_problem_id else ""
        self._send(thread_id, f"Группа {group['id']}{target}: {body}")

    def archive_task(self, thread_id: str) -> None:
        self._archive(thread_id)
