"""Connect dashboard groups to real local Codex tasks."""

from __future__ import annotations

import json
from pathlib import Path
import selectors
import subprocess
from threading import Event, Lock, Thread
import tempfile
import time
from typing import Any, Callable, Mapping


MODEL = "gpt-5.6-terra"
EFFORT = "medium"
AUTOMATION_ACCESS_ARGS = [
    "--config", 'sandbox_mode="danger-full-access"',
    "--config", 'approval_policy="never"',
    "--config", 'mcp_servers.teacherhelper.default_tools_approval_mode="approve"',
    "--config", 'mcp_servers.teacherhelper_org.default_tools_approval_mode="approve"',
]


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
        {"id": 2, "method": method, "params": dict(params)},
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
                return message.get("result") or {}
        raise RuntimeError(f"Codex request timed out: {method}")
    finally:
        selector.close()
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()


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


def _watch(
    process: subprocess.Popen[str],
    thread_id: str,
    on_exit: Callable[[str, int], None] | None,
) -> None:
    return_code = process.wait()
    if on_exit:
        on_exit(thread_id, return_code)


def _create_thread(
    project_root: Path,
    prompt: str,
    model: str,
    effort: str,
    on_exit: Callable[[str, int], None] | None = None,
) -> str:
    output = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False)
    output_path = Path(output.name)
    process = subprocess.Popen(
        [
            "codex", "exec", "--json", *AUTOMATION_ACCESS_ARGS, "-C", str(project_root),
            "-m", model, "-c", f'model_reasoning_effort="{effort}"',
            "--thread-source", "appServer", prompt,
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
                thread_id = str(event["thread_id"])
                Thread(target=_watch, args=(process, thread_id, on_exit), daemon=True).start()
                reader.close()
                output_path.unlink(missing_ok=True)
                return thread_id
        if process.poll() is not None:
            break
        time.sleep(0.05)
    process.terminate()
    reader.close()
    output_path.unlink(missing_ok=True)
    raise RuntimeError("Codex did not create a task")


def _send_message(
    project_root: Path,
    thread_id: str,
    prompt: str,
    on_exit: Callable[[str, int], None] | None = None,
) -> None:
    """Queue a turn in the app-owned task."""

    process = subprocess.run(
        [
            "codex", "queue", "--thread", thread_id, "--message", prompt,
            *AUTOMATION_ACCESS_ARGS, "-C", str(project_root),
        ],
        cwd=project_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if process.returncode and on_exit:
        on_exit(thread_id, process.returncode)


class _SerialMessageSender:
    """Run messages for one Codex task in submission order."""

    def __init__(self, send: Callable[[str, str], None]) -> None:
        self._send = send
        self._lock = Lock()
        self._tails: dict[str, Event] = {}

    def __call__(self, thread_id: str, prompt: str) -> None:
        done = Event()
        with self._lock:
            previous = self._tails.get(thread_id)
            self._tails[thread_id] = done
        Thread(target=self._run, args=(thread_id, prompt, previous, done), daemon=True).start()

    def _run(self, thread_id: str, prompt: str, previous: Event | None, done: Event) -> None:
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
        self._create = create_thread or (lambda prompt, model, effort: _create_thread(project_root, prompt, model, effort, on_exit))
        self._send = send_message or _SerialMessageSender(
            lambda thread_id, prompt: _send_message(project_root, thread_id, prompt, on_exit)
        )
        self._archive = archive_thread or (lambda thread_id: _archive_thread(project_root, thread_id))

    def list_tasks(self) -> list[dict[str, Any]]:
        return [{
            "id": str(item["id"]),
            "title": str(item.get("title") or item.get("name") or str(item.get("preview") or item["id"]).splitlines()[0]),
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
    ) -> dict[str, str]:
        prompt = build_registration_prompt(group, inventory, comment)
        if thread_id:
            task = next((item for item in self.list_tasks() if item["id"] == thread_id), None)
            if task is None:
                raise ValueError("selected Codex task does not exist in this project")
            self._send(thread_id, prompt)
            return {"id": thread_id, "title": str(task["title"])}
        created_id = self._create(prompt, MODEL, EFFORT)
        return {"id": created_id, "title": f"{group['id']} · {group['title']}"}

    def send_comment(self, thread_id: str, group: Mapping[str, Any], body: str, source_problem_id: str | None = None) -> None:
        target = f" · задача {source_problem_id}" if source_problem_id else ""
        self._send(thread_id, f"Группа {group['id']}{target}: {body}")

    def archive_task(self, thread_id: str) -> None:
        self._archive(thread_id)
