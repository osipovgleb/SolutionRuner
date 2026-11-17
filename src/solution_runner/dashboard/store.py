"""SQLite state and filesystem backfill for the local group dashboard."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .store_common import _now, _source_label, _system_column
from .store_runs import discover_latest_runs as _exported_discover_latest_runs
from .store_schema import SCHEMA
from .store_sync import sync_groups as _exported_sync_groups

discover_latest_runs = _exported_discover_latest_runs
sync_groups = _exported_sync_groups


def normalize_group_key(value: str) -> str:
    value = value.strip()
    match = re.fullmatch(r"(?:Группа\s+)?(?:№\s*)?([0-9]+)", value, re.IGNORECASE)
    return match.group(1) if match else value


class DashboardStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            comment_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(comments)")
            }
            if "attachments" not in comment_columns:
                connection.execute(
                    "ALTER TABLE comments ADD COLUMN attachments TEXT NOT NULL DEFAULT '[]'"
                )
            columns = {
                row[1] for row in connection.execute("PRAGMA table_info(groups)")
            }
            migrations = {
                "manual_source": "TEXT",
                "revision_requested": "INTEGER NOT NULL DEFAULT 0",
                "existing_solution_policy": "TEXT NOT NULL DEFAULT 'preserve'",
                "condition_image_policy": "TEXT NOT NULL DEFAULT 'auto'",
                "solution_image_policy": "TEXT NOT NULL DEFAULT 'auto'",
                "verify_answers": "INTEGER NOT NULL DEFAULT 1",
                "verify_helpers": "INTEGER NOT NULL DEFAULT 1",
                "agent_sample_size": "INTEGER NOT NULL DEFAULT 1",
                "codex_thread_id": "TEXT",
                "codex_archived": "INTEGER NOT NULL DEFAULT 0",
                "full_dry_run_status": "TEXT",
                "agent_status": "TEXT",
                "agent_summary": "TEXT",
                "source_navigation": "TEXT",
            }
            for name, definition in migrations.items():
                if name not in columns:
                    connection.execute(
                        f"ALTER TABLE groups ADD COLUMN {name} {definition}"
                    )
            comment_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(comments)")
            }
            if "problem_id" not in comment_columns:
                connection.execute("ALTER TABLE comments ADD COLUMN problem_id TEXT")
            if "author_type" not in comment_columns:
                connection.execute(
                    "ALTER TABLE comments ADD COLUMN author_type TEXT NOT NULL DEFAULT 'user'"
                )
                connection.execute(
                    "INSERT INTO comments (group_key, problem_id, author_type, body, created_at) "
                    "SELECT group_key, NULL, 'codex', agent_summary, synced_at FROM groups "
                    "WHERE agent_summary IS NOT NULL AND agent_summary != ''"
                )

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _group(row: sqlite3.Row) -> dict[str, Any]:
        group = dict(row)
        group["registered"] = bool(group["registered"])
        group["legacy"] = bool(group["legacy"])
        group["revision_requested"] = bool(group["revision_requested"])
        group["codex_archived"] = bool(group["codex_archived"])
        group["verify_answers"] = bool(group["verify_answers"])
        group["verify_helpers"] = bool(group["verify_helpers"])
        navigation = group.pop("source_navigation")
        group["teacherhelper"] = json.loads(navigation) if navigation else None
        manual_column = group.pop("manual_column")
        group["column"] = (
            {
                "needs_input": "issues",
                "blocked": "issues",
                "delivery_failed": "issues",
            }.get(group.get("agent_status"))
            or manual_column
            or group["system_column"]
        )
        group["source"] = group.pop("manual_source") or group["source"]
        group["id"] = group.pop("group_key")
        group["task"] = group["task_title"]
        group["stats"] = {
            "transformed": group["transformed"],
            "total": group["total"],
            "helpers": group["helpers"],
            "errors": group["errors"] + group["blocked"],
            "answers_verified": group["transformed"],
            "answers_unverified": max(group["total"] - group["transformed"], 0),
            "helpers_verified": group["helpers"],
            "helpers_unverified": max(group["total"] - group["helpers"], 0),
        }
        return group

    def list_groups(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM groups ORDER BY title COLLATE NOCASE, group_key"
            ).fetchall()
        return [self._group(row) for row in rows]

    def remove_group(self, group_key: str) -> bool:
        """Remove only the dashboard card; retain inventory and run artifacts."""
        with self.connect() as connection:
            if (
                connection.execute(
                    "SELECT 1 FROM groups WHERE group_key = ?", (group_key,)
                ).fetchone()
                is None
            ):
                return False
            connection.execute(
                "INSERT OR IGNORE INTO removed_groups VALUES (?)", (group_key,)
            )
            connection.execute("DELETE FROM groups WHERE group_key = ?", (group_key,))
        return True

    def prune_inactive_groups(self, active_group_keys: set[str]) -> int:
        """Drop imported profiles/history that are no longer active; keep manual groups."""
        with self.connect() as connection:
            stale = [
                row["group_key"]
                for row in connection.execute(
                    "SELECT group_key FROM groups WHERE registered = 1 OR legacy = 1"
                )
                if row["group_key"] not in active_group_keys
            ]
            connection.executemany(
                "DELETE FROM groups WHERE group_key = ?", ((key,) for key in stale)
            )
        return len(stale)

    def get_group(self, group_key: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM groups WHERE group_key = ?", (group_key,)
            ).fetchone()
        return self._group(row) if row else None

    def reconcile_problem_counts(
        self, group_key: str, items: list[Mapping[str, Any]]
    ) -> None:
        """Keep the card's problem count aligned with the current task index."""
        total = len(items)
        successful = {"applied", "already_complete"}
        transformed = sum(item.get("apply_status") in successful for item in items)
        helpers = sum(item.get("helpers_status") in successful for item in items)
        errors = sum(
            any(
                item.get(field) == "failed"
                for field in ("apply_status", "helpers_status")
            )
            for item in items
        )
        blocked = sum(
            any(
                item.get(field) == "blocked"
                for field in ("apply_status", "helpers_status")
            )
            for item in items
        )
        with self.connect() as connection:
            row = connection.execute(
                "SELECT registered, latest_run FROM groups WHERE group_key = ?",
                (group_key,),
            ).fetchone()
            if row is None:
                return
            system_column = _system_column(
                has_run=bool(row["latest_run"]),
                total=total,
                transformed=transformed,
                helpers=helpers,
                errors=errors,
                blocked=blocked,
            )
            connection.execute(
                "UPDATE groups SET total = ?, transformed = ?, helpers = ?, errors = ?, blocked = ?, system_column = ? WHERE group_key = ?",
                (
                    total,
                    transformed,
                    helpers,
                    errors,
                    blocked,
                    system_column,
                    group_key,
                ),
            )

    def upsert_fact(self, fact: Mapping[str, Any]) -> None:
        columns = (
            "group_key",
            "title",
            "path",
            "source",
            "source_id",
            "registered",
            "legacy",
            "workflow",
            "handler",
            "total",
            "transformed",
            "helpers",
            "errors",
            "blocked",
            "latest_run",
            "run_status",
            "system_column",
            "synced_at",
        )
        values = [fact.get(column) for column in columns]
        updates = ", ".join(
            f"{column}=excluded.{column}" for column in columns if column != "group_key"
        )
        with self.connect() as connection:
            if connection.execute(
                "SELECT 1 FROM removed_groups WHERE group_key = ?", (fact["group_key"],)
            ).fetchone():
                return
            connection.execute(
                f"INSERT INTO groups ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)}) "
                f"ON CONFLICT(group_key) DO UPDATE SET {updates}",
                values,
            )

    def update_group(
        self, group_key: str, changes: Mapping[str, Any]
    ) -> dict[str, Any] | None:
        allowed = {
            "column": "manual_column",
            "title": "title",
            "task_title": "task_title",
            "task_url": "task_url",
            "codex_thread_id": "codex_thread_id",
            "codex_archived": "codex_archived",
            "full_dry_run_status": "full_dry_run_status",
            "agent_status": "agent_status",
            "agent_summary": "agent_summary",
            "teacherhelper": "source_navigation",
            "revision_requested": "revision_requested",
            "existing_solution_policy": "existing_solution_policy",
            "condition_image_policy": "condition_image_policy",
            "solution_image_policy": "solution_image_policy",
            "verify_answers": "verify_answers",
            "verify_helpers": "verify_helpers",
            "agent_sample_size": "agent_sample_size",
        }
        values = {
            allowed[key]: value for key, value in changes.items() if key in allowed
        }
        if "source_navigation" in values:
            values["source_navigation"] = json.dumps(values["source_navigation"])
        agent_column = {
            "working": "work",
            "verifying": "work",
            "updated": "review",
            "no_changes": "review",
            "needs_input": "issues",
            "blocked": "issues",
            "delivery_failed": "issues",
        }.get(changes.get("agent_status"))
        if agent_column and "column" not in changes:
            values["manual_column"] = agent_column
        if (
            values.get("manual_column") in {"review", "done"}
            and "revision_requested" not in changes
        ):
            values["revision_requested"] = 0
        if values.get("manual_column") == "done":
            values["agent_status"] = None
        if not values:
            return self.get_group(group_key)
        assignments = ", ".join(f"{key} = ?" for key in values)
        with self.connect() as connection:
            current = connection.execute(
                "SELECT agent_summary FROM groups WHERE group_key = ?",
                (group_key,),
            ).fetchone()
            connection.execute(
                f"UPDATE groups SET {assignments} WHERE group_key = ?",
                (*values.values(), group_key),
            )
            summary = changes.get("agent_summary")
            if (
                summary
                and changes.get("agent_status")
                in {"updated", "no_changes", "needs_input", "blocked"}
                and (current is None or current["agent_summary"] != summary)
            ):
                connection.execute(
                    "INSERT INTO comments (group_key, problem_id, author_type, body, created_at) "
                    "VALUES (?, NULL, 'codex', ?, ?)",
                    (group_key, summary, _now()),
                )
        return self.get_group(group_key)

    def add_manual_group(
        self,
        group_key: str,
        catalog_snapshot_id: str,
        options: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        options = options or {}
        group_key = normalize_group_key(group_key)
        if self.get_group(group_key) is not None:
            raise ValueError(f"group {group_key} already exists")
        with self.connect() as connection:
            connection.execute(
                "DELETE FROM removed_groups WHERE group_key = ?", (group_key,)
            )
        self.upsert_fact(
            {
                "group_key": group_key,
                "title": f"Группа {group_key}",
                "path": "Ожидает описания агента",
                "source": _source_label(catalog_snapshot_id),
                "source_id": catalog_snapshot_id,
                "registered": 0,
                "legacy": 0,
                "workflow": None,
                "handler": None,
                "total": 0,
                "transformed": 0,
                "helpers": 0,
                "errors": 0,
                "blocked": 0,
                "latest_run": None,
                "run_status": None,
                "system_column": "initialization",
                "synced_at": _now(),
            }
        )
        changes = {
            key: options[key]
            for key in (
                "existing_solution_policy",
                "condition_image_policy",
                "solution_image_policy",
                "verify_answers",
                "verify_helpers",
                "agent_sample_size",
            )
            if key in options
        }
        return self.update_group(group_key, changes)

    def list_comments(self, group_key: str) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT id, problem_id, author_type, body, created_at, attachments FROM comments WHERE group_key = ? ORDER BY id",
                (group_key,),
            ).fetchall()
        return [
            {**dict(row), "attachments": json.loads(row["attachments"])} for row in rows
        ]

    def add_comment(
        self,
        group_key: str,
        body: str,
        problem_id: str | None = None,
        attachments: list | None = None,
    ) -> dict[str, Any]:
        created_at = _now()
        with self.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO comments (group_key, problem_id, author_type, body, created_at, attachments) VALUES (?, ?, 'user', ?, ?, ?)",
                (
                    group_key,
                    problem_id,
                    body,
                    created_at,
                    json.dumps(attachments or []),
                ),
            )
            connection.execute(
                "UPDATE groups SET manual_column = 'work', revision_requested = 1, full_dry_run_status = NULL "
                "WHERE group_key = ? AND COALESCE(manual_column, system_column) IN ('review', 'issues')",
                (group_key,),
            )
        return {
            "id": cursor.lastrowid,
            "problem_id": problem_id,
            "author_type": "user",
            "body": body,
            "created_at": created_at,
            "attachments": attachments or [],
        }
