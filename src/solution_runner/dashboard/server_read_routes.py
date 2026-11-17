"""Read-only HTTP routes and static dashboard content."""

import logging
import mimetypes
from typing import Any
from urllib.parse import parse_qs, urlparse

from .activity import load_group_activity
from .catalogs import load_catalogs
from .previews import (
    ProblemPreviewUnavailable,
    append_preview_sample,
    fetch_preview,
    fetch_problem_preview,
    latest_dry_run_manifest,
    load_preview,
    save_preview,
)


def _summary(groups: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "groups": len(groups),
        "transformed": sum(group["transformed"] for group in groups),
        "helpers": sum(group["helpers"] for group in groups),
        "errors": sum(group["stats"]["errors"] for group in groups),
    }


class DashboardReadRoutes:
    def do_GET(self) -> None:
        segments = self._segments()
        for handler in (
            self._get_global,
            self._get_group_state,
            self._get_group_tasks,
            self._get_task_preview,
            self._get_group_details,
        ):
            if handler(segments):
                return
        self._static()

    def _get_global(self, segments: list[str]) -> bool:
        if len(segments) == 3 and segments[:2] == ["api", "comment-images"]:
            root = (self.server.var_dir / "dashboard/comment-images").resolve()
            path = (root / segments[2]).resolve()
            if path.parent != root or not path.is_file():
                self._json(404, {"error": "image_not_found"})
                return True
            data = path.read_bytes()
            self.send_response(200)
            self.send_header(
                "Content-Type",
                mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            )
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)
            return True
        if segments == ["api", "jobs"] and self.server.job_queue is not None:
            group_key = parse_qs(urlparse(self.path).query).get("group", [None])[0]
            self._json(
                200, {"jobs": self.server.job_queue.list_jobs(group_key=group_key)}
            )
            return True
        if (
            len(segments) == 4
            and segments[:2] == ["api", "jobs"]
            and segments[3] == "log"
        ):
            try:
                if self.server.job_queue is None:
                    raise KeyError(segments[2])
                content = self.server.job_queue.log_tail(int(segments[2]))
            except (ValueError, KeyError):
                self._json(404, {"error": "job_not_found"})
            else:
                self._json(200, {"log": content})
            return True
        if segments == ["api", "codex", "tasks"]:
            if self.server.codex_tasks is None:
                self._json(503, {"error": "codex_tasks_unavailable"})
                return True
            try:
                tasks = self.server.codex_tasks.list_tasks()
            except RuntimeError as exc:
                self._json(
                    502, {"error": "codex_tasks_unavailable", "message": str(exc)}
                )
            else:
                self._json(200, {"tasks": tasks})
            return True
        if segments == ["api", "groups"]:
            groups = self.server.store.list_groups()
            for group in groups:
                self._group_payload(group)
            self._json(
                200,
                {
                    "groups": groups,
                    "summary": _summary(groups),
                    "catalogs": [
                        {"id": key, "name": name}
                        for key, name in load_catalogs().items()
                    ],
                },
            )
            return True
        return False

    def _get_group_state(self, segments: list[str]) -> bool:
        if (
            len(segments) == 4
            and segments[:2] == ["api", "groups"]
            and segments[3] == "comments"
        ):
            self._json(200, {"comments": self.server.store.list_comments(segments[2])})
            return True
        if (
            len(segments) == 4
            and segments[:2] == ["api", "groups"]
            and segments[3] == "preview"
        ):
            preview = load_preview(self.server.preview_dir, segments[2])
            profile = self.server.profiles.get(segments[2])
            if (
                preview is None
                and profile is not None
                and self.server.preview_gateway_factory is not None
            ):
                gateway = self.server.preview_gateway_factory()
                try:
                    manifest = latest_dry_run_manifest(self.server.var_dir, segments[2])
                    if manifest is not None:
                        preview = fetch_preview(gateway, profile, manifest)
                        save_preview(self.server.preview_dir, preview)
                finally:
                    close = getattr(gateway, "close", None)
                    if callable(close):
                        close()
            self._json(200, preview) if preview else self._json(
                404, {"error": "preview_not_found"}
            )
            return True
        if (
            len(segments) == 4
            and segments[:2] == ["api", "groups"]
            and segments[3] == "dry-run"
        ):
            state = (
                self.server.dry_runs.get(segments[2]) if self.server.dry_runs else None
            )
            self._json(200, state) if state else self._json(
                404, {"error": "dry_run_not_found"}
            )
            return True
        if (
            len(segments) == 4
            and segments[:2] == ["api", "groups"]
            and segments[3] == "apply"
        ):
            state = (
                self.server.applies.get(segments[2]) if self.server.applies else None
            )
            self._json(200, state) if state else self._json(
                404, {"error": "apply_not_found"}
            )
            return True
        if (
            len(segments) == 4
            and segments[:2] == ["api", "groups"]
            and segments[3] == "initialization"
        ):
            state = (
                self.server.initializer.get(segments[2])
                if self.server.initializer
                else None
            )
            self._json(200, state) if state else self._json(
                503, {"error": "initializer_unavailable"}
            )
            return True
        return False

    def _get_group_tasks(self, segments: list[str]) -> bool:
        if (
            len(segments) == 4
            and segments[:2] == ["api", "groups"]
            and segments[3] == "tasks"
        ):
            inventory = self.server.inventory_store
            snapshot = inventory.get(segments[2]) if inventory else None
            if snapshot is None:
                self._json(404, {"error": "inventory_not_found"})
                return True
            assets_by_problem: dict[str, list[dict[str, str]]] = {}
            for asset in snapshot.assets:
                assets_by_problem.setdefault(asset.problem_id, []).append(
                    {
                        "asset_id": asset.asset_id,
                        "asset_key": asset.asset_key,
                        "section": asset.section_key,
                        "content_type": asset.content_type,
                    }
                )
            tasks = inventory.list_items(segments[2])
            for task in tasks:
                task["assets"] = assets_by_problem.get(str(task["problem_id"]), [])
            self._json(
                200,
                {
                    "status": snapshot.status,
                    "error": snapshot.error,
                    "parent_problem_id": snapshot.parent_problem_id,
                    "tasks": tasks,
                },
            )
            return True
        return False

    def _get_task_preview(self, segments: list[str]) -> bool:
        if (
            len(segments) == 6
            and segments[:2] == ["api", "groups"]
            and segments[3] == "tasks"
            and segments[5] == "preview"
        ):
            inventory = self.server.inventory_store
            task = next(
                (
                    item
                    for item in (inventory.list_items(segments[2]) if inventory else [])
                    if str(item.get("problem_id")) == segments[4]
                ),
                None,
            )
            if task is None:
                self._json(404, {"error": "problem_not_found"})
                return True
            if self.server.preview_gateway_factory is None:
                self._json(503, {"error": "preview_unavailable"})
                return True
            gateway = self.server.preview_gateway_factory()
            preview = None
            try:
                profile = self.server.profiles.get(segments[2])
                if profile is not None:
                    try:
                        cached = append_preview_sample(
                            gateway,
                            profile,
                            self.server.preview_dir,
                            self.server.var_dir,
                            source_problem_id=str(task["source_problem_id"]),
                        )
                        preview = {
                            **cached,
                            "samples": [
                                sample
                                for sample in cached.get("samples", [])
                                if str(sample.get("problem_id")) == segments[4]
                            ],
                        }
                    except ValueError:
                        logging.getLogger(__name__).debug(
                            "Saved preview could not be refreshed"
                        )
                if not preview or not preview.get("samples"):
                    preview = fetch_problem_preview(
                        gateway,
                        self.server.preview_dir,
                        segments[2],
                        segments[4],
                        str(task["source_problem_id"]),
                    )
            except ProblemPreviewUnavailable:
                self._json(404, {"error": "problem_not_available"})
            finally:
                close = getattr(gateway, "close", None)
                if callable(close):
                    close()
            if preview is not None:
                self._json(200, preview)
            return True
        return False

    def _get_group_details(self, segments: list[str]) -> bool:
        if (
            len(segments) == 4
            and segments[:2] == ["api", "groups"]
            and segments[3] == "activity"
        ):
            if self.server.store.get_group(segments[2]) is None:
                self._json(404, {"error": "group_not_found"})
                return True
            self._json(
                200,
                load_group_activity(
                    self.server.var_dir, segments[2], self.server.inventory_store
                ),
            )
            return True
        if len(segments) == 3 and segments[:2] == ["api", "groups"]:
            group = self._group_payload(self.server.store.get_group(segments[2]))
            self._json(200, group) if group else self._json(
                404, {"error": "group_not_found"}
            )
            return True
        return False

    def _static(self) -> None:
        path = urlparse(self.path).path.lstrip("/") or "index.html"
        candidate = (self.server.static_dir / path).resolve()
        root = self.server.static_dir.resolve()
        if root not in candidate.parents and candidate != root:
            self.send_error(404)
            return
        if not candidate.is_file():
            candidate = root / "index.html"
        if not candidate.is_file():
            self.send_error(404, "Dashboard build not found")
            return
        body = candidate.read_bytes()
        self.send_response(200)
        self.send_header(
            "Content-Type",
            mimetypes.guess_type(candidate.name)[0] or "application/octet-stream",
        )
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
