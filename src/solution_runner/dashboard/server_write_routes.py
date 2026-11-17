"""Mutation HTTP routes for dashboard actions."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .attachments import save_images
from .rejections import reject_indexed_problem
from .store import normalize_group_key


@dataclass(frozen=True)
class CommentDelivery:
    group_key: str
    thread_id: str
    group: dict[str, Any]
    body: str
    source_problem_id: str | None
    image_paths: tuple[Path, ...]


class DashboardWriteRoutes:
    def do_POST(self) -> None:
        if int(self.headers.get("Content-Length", "0")) > 29 * 1024 * 1024:
            self._json(413, {"message": "Вложения превышают допустимый размер."})
            return
        segments = self._segments()
        for handler in (
            self._post_codex,
            self._post_rejection,
            self._post_stages,
            self._post_groups,
            self._post_comment,
        ):
            if handler(segments):
                return
        self._json(404, {"error": "not_found"})

    def _post_codex(self, segments: list[str]) -> bool:
        from .server import _register_group_task

        if (
            len(segments) == 4
            and segments[:2] == ["api", "groups"]
            and segments[3] == "archive-codex"
        ):
            group = self.server.store.get_group(segments[2])
            if group is None:
                self._json(404, {"error": "group_not_found"})
                return True
            if group["column"] != "done":
                self._json(409, {"error": "group_not_done"})
                return True
            thread_id = group.get("codex_thread_id")
            if not thread_id or self.server.codex_tasks is None:
                self._json(409, {"error": "codex_task_not_linked"})
                return True
            if group.get("codex_archived"):
                self._json(200, {"group": self._group_payload(group)})
                return True
            try:
                self.server.codex_tasks.archive_task(str(thread_id))
            except RuntimeError as exc:
                self._json(502, {"error": "codex_archive_failed", "message": str(exc)})
                return True
            updated = self.server.store.update_group(segments[2], {"codex_archived": 1})
            self._json(200, {"group": self._group_payload(updated)})
            return True
        if (
            len(segments) == 4
            and segments[:2] == ["api", "groups"]
            and segments[3] == "register"
        ):
            if self.server.codex_tasks is None or self.server.inventory_store is None:
                self._json(503, {"error": "codex_registration_unavailable"})
                return True
            body = self._body()
            thread_id = str(body.get("thread_id") or "").strip() or None
            comment = str(body.get("comment") or "").strip()
            try:
                task, updated = _register_group_task(
                    self.server.store,
                    self.server.inventory_store,
                    self.server.codex_tasks,
                    segments[2],
                    thread_id,
                    comment,
                )
            except KeyError:
                self._json(404, {"error": "group_inventory_not_found"})
                return True
            except ValueError as exc:
                self._json(409, {"error": "invalid_codex_task", "message": str(exc)})
                return True
            except RuntimeError as exc:
                self._json(
                    502, {"error": "codex_registration_failed", "message": str(exc)}
                )
                return True
            self._json(202, {"task": task, "group": self._group_payload(updated)})
            return True
        return False

    def _post_rejection(self, segments: list[str]) -> bool:
        if (
            len(segments) == 6
            and segments[:2] == ["api", "groups"]
            and segments[3] == "tasks"
            and segments[5] == "reject"
        ):
            if (
                self.server.preview_gateway_factory is None
                or self.server.inventory_store is None
            ):
                self._json(503, {"error": "rejection_unavailable"})
                return True
            reason = str(self._body().get("reason") or "").strip()
            if not reason:
                self._json(400, {"error": "reason_required"})
                return True
            gateway = self.server.preview_gateway_factory()
            try:
                rejection = reject_indexed_problem(
                    gateway,
                    self.server.inventory_store,
                    self.server.preview_dir,
                    segments[2],
                    segments[4],
                    reason,
                )
            except KeyError:
                self._json(404, {"error": "problem_not_found"})
                return True
            except ValueError as exc:
                self._json(
                    409, {"error": "problem_not_rejectable", "message": str(exc)}
                )
                return True
            except RuntimeError:
                self._json(502, {"error": "rejection_not_confirmed"})
                return True
            finally:
                close = getattr(gateway, "close", None)
                if callable(close):
                    close()
            items = self.server.inventory_store.list_items(segments[2])
            self.server.store.reconcile_problem_counts(segments[2], items)
            self._json(
                200,
                {
                    "rejection": rejection,
                    "group": self._group_payload(
                        self.server.store.get_group(segments[2])
                    ),
                },
            )
            return True
        return False

    def _post_stages(self, segments: list[str]) -> bool:
        from .server import _refresh_server_profiles

        if (
            len(segments) == 4
            and segments[:2] == ["api", "groups"]
            and segments[3] == "initialization"
        ):
            if self.server.initializer is None:
                self._json(503, {"error": "initializer_unavailable"})
                return True
            try:
                state = self.server.initializer.start(segments[2])
            except (KeyError, ValueError):
                self._json(404, {"error": "group_not_found"})
            except RuntimeError as exc:
                self._json(
                    409, {"error": "initialization_not_started", "message": str(exc)}
                )
            else:
                self._json(202, state)
            return True
        if (
            len(segments) == 4
            and segments[:2] == ["api", "groups"]
            and segments[3] == "dry-run"
        ):
            if self.server.dry_runs is None:
                self._json(503, {"error": "dry_runs_unavailable"})
                return True
            body = self._body()
            mode = str(body.get("mode") or "")
            try:
                if segments[2] not in self.server.profiles:
                    _refresh_server_profiles(self.server)
                if mode == "problem":
                    state = self.server.dry_runs.start_problem(
                        segments[2], str(body.get("problem_id") or "")
                    )
                else:
                    state = self.server.dry_runs.start(segments[2], mode)
            except KeyError:
                self._json(404, {"error": "group_profile_not_found"})
            except ValueError:
                self._json(400, {"error": "invalid_dry_run_mode"})
            except RuntimeError:
                self._json(409, {"error": "dry_run_already_active"})
            else:
                self._json(202, state)
            return True
        if (
            len(segments) == 4
            and segments[:2] == ["api", "groups"]
            and segments[3] == "apply"
        ):
            if self.server.applies is None:
                self._json(503, {"error": "applies_unavailable"})
                return True
            body = self._body()
            problem_id = str(body.get("problem_id") or "")
            try:
                if body.get("stage") == "helpers":
                    state = self.server.applies.start_helpers(
                        segments[2],
                        None if body.get("scope") == "group" else problem_id,
                    )
                else:
                    if body.get("scope") == "group":
                        state = self.server.applies.start_group(segments[2])
                    elif body.get("force"):
                        state = self.server.applies.start(
                            segments[2], problem_id, force=True
                        )
                    else:
                        state = self.server.applies.start(segments[2], problem_id)
            except KeyError:
                self._json(404, {"error": "group_profile_not_found"})
            except ValueError as exc:
                self._json(409, {"error": "problem_not_ready", "message": str(exc)})
            except RuntimeError:
                self._json(409, {"error": "apply_already_active"})
            else:
                self._json(202, state)
            return True
        return False

    def _post_groups(self, segments: list[str]) -> bool:
        from .server import sync_groups

        if (
            len(segments) == 4
            and segments[:2] == ["api", "groups"]
            and segments[3] == "preview"
        ):
            if self.server.dry_runs is None:
                self._json(503, {"error": "dry_runs_unavailable"})
                return True
            try:
                state = self.server.dry_runs.start_additional(segments[2])
            except ValueError:
                self._json(409, {"error": "preview_task_not_found"})
            except RuntimeError:
                self._json(409, {"error": "dry_run_already_active"})
            else:
                self._json(202, state)
            return True
        if segments == ["api", "groups"]:
            body = self._body()
            group_key = normalize_group_key(str(body.get("id", "")))
            catalog_id = str(body.get("catalog_id", "")).strip()
            if not group_key or not catalog_id:
                self._json(400, {"error": "group_id_and_catalog_required"})
                return True
            try:
                group = self.server.store.add_manual_group(group_key, catalog_id, body)
            except ValueError:
                self._json(409, {"error": "group_already_exists"})
                return True
            note = str(body.get("note", "")).strip()
            if note:
                self.server.store.add_comment(group_key, note)
            if self.server.initializer is not None:
                self.server.initializer.start(group_key)
            else:
                group = self.server.store.update_group(
                    group_key,
                    {
                        "agent_status": "blocked",
                        "agent_summary": "Инициализация недоступна: dashboard запущен без TeacherHelper API key.",
                    },
                )
            self._json(201, self._group_payload(group))
            return True
        if segments == ["api", "sync"]:
            result = sync_groups(
                self.server.store,
                self.server.profiles,
                self.server.var_dir,
                inventory_store=self.server.inventory_store,
            )
            self._json(200, result)
            return True
        return False

    def _post_comment(self, segments: list[str]) -> bool:
        if not (
            len(segments) == 4
            and segments[:2] == ["api", "groups"]
            and segments[3] == "comments"
        ):
            return False
        self._create_comment(segments)
        return True

    def _create_comment(self, segments: list[str]) -> None:
        group = self.server.store.get_group(segments[2])
        if group is None:
            self._json(404, {"error": "group_not_found"})
            return
        payload = self._body()
        body = str(payload.get("body", "")).strip()
        if not body and not payload.get("images"):
            self._json(400, {"error": "comment_required"})
            return
        problem_id = str(payload.get("problem_id") or "").strip() or None
        source_problem_id = None
        if problem_id:
            item = next(
                (
                    item
                    for item in (
                        self.server.inventory_store.list_items(segments[2])
                        if self.server.inventory_store
                        else []
                    )
                    if str(item.get("problem_id")) == problem_id
                ),
                None,
            )
            if item is None:
                self._json(404, {"error": "problem_not_found"})
                return
            source_problem_id = str(item["source_problem_id"])
        thread_id = group.get("codex_thread_id")
        image_root = self.server.var_dir / "dashboard/comment-images"
        if payload.get("images") and not thread_id:
            self._json(
                409,
                {
                    "error": "codex_task_not_linked",
                    "message": "Сначала свяжите группу с Codex.",
                },
            )
            return
        if thread_id and self.server.codex_tasks is None:
            self._json(503, {"error": "codex_tasks_unavailable"})
            return
        try:
            attachments = save_images(image_root, payload.get("images", []))
        except ValueError as exc:
            self._json(400, {"error": "invalid_images", "message": str(exc)})
            return
        image_paths = tuple(
            image_root / item["url"].rsplit("/", 1)[-1] for item in attachments
        )
        must_send = (
            group["column"] in {"issues", "review"}
            or group.get("agent_status")
            in {"blocked", "needs_input", "delivery_failed"}
            or problem_id
        )
        sent_to_codex = False
        if thread_id:
            request = CommentDelivery(
                segments[2], str(thread_id), group, body, source_problem_id, image_paths
            )
            if not self._send_codex_comment(request):
                return
            sent_to_codex = True
        elif must_send:
            self._json(409, {"error": "codex_task_not_linked"})
            return
        comment = self.server.store.add_comment(
            segments[2], body, problem_id, attachments=attachments
        )
        if sent_to_codex:
            self.server.store.update_group(
                segments[2],
                {
                    "agent_status": "working",
                    "agent_summary": None,
                },
            )
        self._json(
            201,
            {
                "comment": comment,
                "group": self._group_payload(self.server.store.get_group(segments[2])),
            },
        )
        return

    def _send_codex_comment(self, request: CommentDelivery) -> bool:
        thread_id = request.thread_id
        group = request.group
        body = request.body
        source_problem_id = request.source_problem_id
        image_paths = request.image_paths
        if self.server.codex_tasks is None:
            self._json(503, {"error": "codex_tasks_unavailable"})
            return False
        try:
            if image_paths:
                self.server.codex_tasks.send_comment(
                    str(thread_id),
                    group,
                    body,
                    source_problem_id,
                    images=image_paths,
                )
            elif source_problem_id:
                self.server.codex_tasks.send_comment(
                    str(thread_id), group, body, source_problem_id
                )
            else:
                self.server.codex_tasks.send_comment(str(thread_id), group, body)
        except RuntimeError as exc:
            # A timeout may follow queue acceptance; retain local files
            # so the native owner can still read admitted attachments.
            self.server.store.update_group(
                request.group_key,
                {
                    "agent_status": "delivery_failed",
                    "agent_summary": str(exc)[:200],
                },
            )
            self._json(502, {"error": "codex_comment_failed", "message": str(exc)})
            return False
        return True
