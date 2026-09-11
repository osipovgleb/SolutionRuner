"""Connect dashboard groups to real local Codex tasks."""

from __future__ import annotations

import json
from pathlib import Path
import selectors
import subprocess
from threading import Thread
import tempfile
import time
from typing import Any, Callable, Mapping


MODEL = "gpt-5.6-terra"
EFFORT = "medium"


def build_registration_prompt(group: Mapping[str, Any], inventory: Mapping[str, Any]) -> str:
    """Build the bounded, repeatable prompt used for group registration."""

    return f"""{group['id']} · {group['title']}

Зарегистрируй группу SolutionRunner {group['id']} — «{group['title']}».

Источник истины — локальный SQLite-индекс дэшборда `var/dashboard/dashboard.sqlite3`. Не используй старые manifest-файлы как реестр.
В группе {inventory['task_count']} задач; родитель: локальный ID {inventory['parent_problem_id']}, source ID {inventory['parent_source_problem_id']}.

Сначала найди в SQLite все незакрытые проблемы именно этой группы: соедини `group_item_stage_results` и `group_inventory_items` по `group_key` и `problem_id`; изучи `dry_run_error`, `apply_error`, `error` и статусы Apply/Helpers. Для каждой причины зафиксируй внешний `source_problem_id` и объясни, какой этап раннера её вызвал. Не останавливайся на том, что профиль уже зарегистрирован: если есть хотя бы одна проблема, сначала исследуй её карточку и только затем решай, нужна ли правка.

Затем изучи проблемные задачи через TeacherHelper MCP, соседние зарегистрированные группы и существующие раннеры. Подбери наиболее близкий раннер: переиспользуй или минимально адаптируй его; создавай новый только если подходящего действительно нет. После изменения технически проверь родителя и каждую проблемную задачу без внешней записи.

Не запускай полный dry-run группы: пользователь запускает его из дэшборда. После изменения допустим только точечный dry-run проблемных задач; полный dry-run не запускай автоматически. Не выполняй Apply, Helpers или Reject через MCP. Не используй навыки `superpowers`. Не коммить и не пушь изменения.

Перед финальным сообщением обязательно обнови карточку этой группы в SQLite через `DashboardStore(...).update_group(...)`: выставь `agent_status` в `updated`, `no_changes` или `blocked`, а в `agent_summary` запиши короткий итог (до 200 символов) с проблемным `source_problem_id` и результатом. Карточка — обязательный итог работы, а не только сообщение в треде."""


def build_feedback_prompt(group: Mapping[str, Any], body: str, source_problem_id: str | None = None) -> str:
    target = f" по задаче {source_problem_id}" if source_problem_id else ""
    return f"""Комментарий пользователя по группе {group['id']} — «{group['title']}»{target}:

{body}

Продолжи работу над раннером с учётом комментария. Не выполняй Apply или Reject через MCP и не запускай полный dry-run автоматически. После локальной проверки обнови карточку группы в `var/dashboard/dashboard.sqlite3` через `DashboardStore(...).update_group(...)`: `agent_status` — `updated`, `no_changes` или `blocked`, `agent_summary` — краткий итог до 200 символов. Затем сообщи результат в этой задаче."""


def _list_threads(project_root: Path) -> list[dict[str, Any]]:
    process = subprocess.Popen(
        ["codex", "app-server", "--stdio"],
        cwd=project_root,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    assert process.stdin is not None and process.stdout is not None
    messages = [
        {"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "solution-runner-dashboard", "title": "SolutionRunner", "version": "1.0"},
            "capabilities": {"experimentalApi": True},
        }},
        {"method": "initialized", "params": {}},
        {"id": 2, "method": "thread/list", "params": {
            "cwd": str(project_root), "limit": 100, "archived": False,
        }},
    ]
    for message in messages:
        process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + 8
    try:
        while time.monotonic() < deadline:
            if not selector.select(timeout=max(deadline - time.monotonic(), 0)):
                break
            line = process.stdout.readline()
            if not line:
                break
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if message.get("id") == 2:
                if message.get("error"):
                    raise RuntimeError(str(message["error"]))
                result = message.get("result") or {}
                return [item for item in result.get("data", []) if isinstance(item, dict)]
        raise RuntimeError("Codex task list timed out")
    finally:
        selector.close()
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()


def _wait(process: subprocess.Popen[str]) -> None:
    process.wait()


def _create_thread(project_root: Path, prompt: str, model: str, effort: str) -> str:
    output = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False)
    output_path = Path(output.name)
    process = subprocess.Popen(
        [
            "codex", "exec", "--json", "-C", str(project_root),
            "-m", model, "-c", f'model_reasoning_effort="{effort}"',
            "-s", "workspace-write", "--thread-source", "appServer", prompt,
        ],
        cwd=project_root,
        stdout=output,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    output.close()
    reader = output_path.open(encoding="utf-8")
    deadline = time.monotonic() + 15
    position = 0
    while time.monotonic() < deadline:
        reader.seek(position)
        lines = reader.readlines()
        position = reader.tell()
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "thread.started" and event.get("thread_id"):
                Thread(target=_wait, args=(process,), daemon=True).start()
                reader.close()
                output_path.unlink(missing_ok=True)
                return str(event["thread_id"])
        if process.poll() is not None:
            break
        time.sleep(0.05)
    process.terminate()
    reader.close()
    output_path.unlink(missing_ok=True)
    raise RuntimeError("Codex did not create a task")


def _send_message(project_root: Path, thread_id: str, prompt: str) -> None:
    """Resume the task with a user message instead of merely queueing it."""

    process = subprocess.Popen(
        ["codex", "exec", "resume", "--json", thread_id, prompt],
        cwd=project_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        start_new_session=True,
    )
    time.sleep(0.15)
    if process.poll() is not None:
        raise RuntimeError("Codex task did not start")


class CodexTaskService:
    def __init__(
        self,
        *,
        project_root: Path,
        list_threads: Callable[[], list[dict[str, Any]]] | None = None,
        create_thread: Callable[[str, str, str], str] | None = None,
        send_message: Callable[[str, str], None] | None = None,
    ) -> None:
        self.project_root = project_root
        self._list = list_threads or (lambda: _list_threads(project_root))
        self._create = create_thread or (lambda prompt, model, effort: _create_thread(project_root, prompt, model, effort))
        self._send = send_message or (lambda thread_id, prompt: _send_message(project_root, thread_id, prompt))

    def list_tasks(self) -> list[dict[str, Any]]:
        return [{
            "id": str(item["id"]),
            "title": str(item.get("title") or item.get("name") or item.get("preview") or item["id"]),
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
    ) -> dict[str, str]:
        prompt = build_registration_prompt(group, inventory)
        if thread_id:
            task = next((item for item in self.list_tasks() if item["id"] == thread_id), None)
            if task is None:
                raise ValueError("selected Codex task does not exist in this project")
            self._send(thread_id, prompt)
            return {"id": thread_id, "title": str(task["title"])}
        created_id = self._create(prompt, MODEL, EFFORT)
        return {"id": created_id, "title": f"{group['id']} · {group['title']}"}

    def send_comment(self, thread_id: str, group: Mapping[str, Any], body: str, source_problem_id: str | None = None) -> None:
        self._send(thread_id, build_feedback_prompt(group, body, source_problem_id))
