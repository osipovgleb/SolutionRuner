#!/usr/bin/env python3
"""Discover current grid-polygon PNGs and replace them through TeacherHelper MCP."""

from __future__ import annotations

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import io
import json
import os
import sys
import threading
import time
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Sequence, TypeVar
from urllib.parse import urljoin
from uuid import UUID

import httpx
from PIL import Image


DEFAULT_MCP_URL = "https://lessons-helper.ru/mcp"
DEFAULT_CATALOG_SNAPSHOT_ID = "4073fc7b-2056-4697-b18b-38741c94d0f4"
DEFAULT_SOURCE_SITE_ID = "7bed2492-5b8b-4c88-9be8-7d47916cd7c6"
DEFAULT_CATEGORY_KEY = "9"
DEFAULT_CATEGORY_TITLE = "9. Задачи на квадратной решетке"
DEFAULT_THEME_TITLES = (
    "Трапеция",
    "Треугольник",
    "Ромб",
    "Произвольный четырехугольник",
)
EXPECTED_VERTICES_BY_THEME = {
    "Трапеция": 4,
    "Треугольник": 3,
    "Ромб": 4,
    "Произвольный четырехугольник": 4,
}
FIXED_THEME_CONFIG = {
    "Трапеция": {
        "snapshot_theme_id": "26af5056-7c19-4148-85a2-ce95069d8760",
        "source_theme_id": "284",
        "order_index": 2,
        "source_groups_count": 7,
    },
    "Треугольник": {
        "snapshot_theme_id": "3913765c-3750-456e-aaff-2fc050bc8821",
        "source_theme_id": "286",
        "order_index": 3,
        "source_groups_count": 8,
    },
    "Ромб": {
        "snapshot_theme_id": "785f5813-b3f0-41cd-b6a1-6c63c4223d5e",
        "source_theme_id": "285",
        "order_index": 4,
        "source_groups_count": 1,
    },
    "Произвольный четырехугольник": {
        "snapshot_theme_id": "3bfd66e9-836c-4eda-a293-9885053ec4bd",
        "source_theme_id": "122",
        "order_index": 5,
        "source_groups_count": 23,
    },
}
FIXED_SOURCE_GROUPS = {
    "Трапеция": (
        ("fc5fc7a7-75ba-41d4-9bb7-4fee7b1b8be1", "27556"),
        ("ae4b8e1f-4ff2-4085-aee5-d3be39ccdbd6", "27557"),
        ("416046da-eecc-4473-83fd-b1b6c799a7e6", "27558"),
        ("0719750c-08ff-450c-bc16-3a65989caf9a", "27559"),
        ("3fb2e89d-9858-4c76-9683-d2d348ce4a35", "27560"),
        ("f2422780-bacb-4231-a06a-b89e855fc801", "244985"),
        ("0be1e4bb-4e88-43d0-8f03-2d4b1440773c", "244986"),
    ),
    "Треугольник": (
        ("4808d0b7-aa63-4a5f-85ed-da28c8f80b18", "27543"),
        ("b8fcbdc6-7967-4bc0-99b1-3fa49d5d824f", "27544"),
        ("0d938f6c-b012-4013-8dad-778add652e11", "27545"),
        ("d371408f-f616-4ed0-9cea-85f27fc30c4e", "27546"),
        ("96309f98-73c1-4abc-8005-73a4307e7295", "27547"),
        ("7e1ba8c1-23dc-4e04-aec2-67e23ef52cc7", "27548"),
        ("3e818284-d58c-43a6-b7b4-c21a48e5a425", "27549"),
        ("a3e9590e-400a-4e2e-9fcc-a4ddc94e53ab", "244982"),
    ),
    "Ромб": (
        ("c7fb645b-bb12-48f9-86c9-de6bd980389e", "244983"),
    ),
    "Произвольный четырехугольник": (
        ("0efa9c9d-8b0a-4eda-8f91-3bab53034f85", "27553"),
        ("8692d319-27c2-4e8b-994a-6efa20a7adac", "27554"),
        ("e779214c-ef69-400f-9516-db1e3cec409d", "27555"),
        ("65378636-e6f5-4087-8d36-37bf60e01556", "244987"),
        ("21f4102f-5758-4069-8ade-e35d3c1a91e4", "244988"),
        ("07db163e-8cb4-4fb9-abda-11ea84c72697", "244989"),
        ("c1720bed-72fd-4c28-8cc8-ab67cbab3449", "244990"),
        ("500815ad-983f-4658-820c-e63a4c3ca08e", "244991"),
        ("dfbc0d00-a0ee-4e3e-8791-369cf64339cc", "244992"),
        ("482c8645-573c-4d09-962a-10f9347e346a", "244993"),
        ("4af236f2-0dc6-44d1-b99e-d604fbe803b3", "244994"),
        ("1de2d522-204a-439e-99c1-37eb45881192", "244995"),
        ("07793db5-7983-4a49-81fc-2a1c04a21599", "244996"),
        ("c311c7ee-6156-4164-b052-dee139e6feb4", "244997"),
        ("a56949ab-bcc3-409d-8375-a216927ed92a", "244998"),
        ("a6c625ec-3b46-48ff-a1d5-a4518995a144", "244999"),
        ("d4f8b1b5-4a4f-4cca-9523-fcd32ac1e8f0", "245000"),
        ("8fa38806-4fb0-45d2-98e8-da85dc47ff1b", "245001"),
        ("07702ba0-2f65-4693-a842-cf44c1a0b194", "245002"),
        ("d0d1abe1-9b69-479d-8f43-b6f9182e861f", "245003"),
        ("5934b527-a4dc-49aa-95c5-4e748661b4f2", "245004"),
        ("186ffd8e-c830-476e-8361-98e8ba5dadf8", "245006"),
        ("2d78a6aa-7d44-4509-ac8e-534dc0a59349", "245007"),
    ),
}
REQUIRED_MCP_TOOLS = {
    "get_asset",
    "get_asset_file",
    "get_problem_asset_target_context",
    "get_problem_pipeline_state",
    "get_problem_transformation_context",
    "get_source_asset",
    "get_source_catalog_children",
    "get_source_catalog_section_images",
    "delete_problem_transformation",
    "prepare_source_asset_upload",
    "replace_problem_asset",
}
REQUIRED_ROLLBACK_MCP_TOOLS = {"delete_problem_transformation"}
PNG_CONTENT_TYPE = "image/png"
BMP_CONTENT_TYPES = frozenset({"image/bmp", "image/x-ms-bmp"})
RASTER_CONTENT_TYPES = frozenset({PNG_CONTENT_TYPE, *BMP_CONTENT_TYPES})
SVG_CONTENT_TYPE = "image/svg+xml"
MCP_PROTOCOL_VERSION = "2025-06-18"
CONVERTER_PROFILE = "grid-polygon-svg-v1"
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_RED = "\033[31m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_BLUE = "\033[34m"
ANSI_MAGENTA = "\033[35m"
ANSI_CYAN = "\033[36m"
ANSI_BRIGHT_GREEN = "\033[92m"
TASK_STAGE_STYLES = {
    "source_downloaded": ("DOWNLOADED", ANSI_BLUE),
    "asset_prepared": ("CONVERTED", ANSI_MAGENTA),
    "upload_link_created": ("UPLOAD URL READY", ANSI_CYAN),
    "svg_uploaded": ("SVG UPLOADED", ANSI_GREEN),
    "asset_replaced": ("TRANSFORMATION APPLIED", ANSI_BRIGHT_GREEN),
    "asset_rolled_back": ("TRANSFORMATION ROLLED BACK", ANSI_BRIGHT_GREEN),
    "rollback_stale": ("SKIPPED / CHANGED", ANSI_YELLOW),
    "asset_rejected": ("REJECTED", ANSI_YELLOW),
    "asset_stale": ("SKIPPED / STALE", ANSI_YELLOW),
    "asset_error": ("ERROR", ANSI_RED),
}

_T = TypeVar("_T")
_R = TypeVar("_R")


class PipelineError(RuntimeError):
    """Base class for deterministic pipeline failures."""


class McpCallError(PipelineError):
    """Report one failed MCP JSON-RPC call without exposing credentials."""


class CandidateRejected(PipelineError):
    """Mark an input that deterministically fails conversion or validation."""


class CandidateStale(PipelineError):
    """Mark a candidate whose current MCP state no longer matches inventory."""


@dataclass(frozen=True)
class ThemeScope:
    """Hold one exact theme from the fixed production scope."""

    title: str
    snapshot_theme_id: str
    source_theme_id: str
    order_index: int
    source_groups_count: int
    expected_vertices: int


@dataclass(frozen=True)
class GroupScope:
    """Hold one exact ordered source group from the fixed production scope."""

    source_group_id: str
    group_key: str
    order_index: int


@dataclass(frozen=True)
class AssetCandidate:
    """Identify one current ordinary PNG in an eligible concrete problem."""

    theme_title: str
    snapshot_theme_id: str
    theme_order_index: int
    source_group_id: str
    group_key: str
    group_order_index: int
    problem_id: str
    source_problem_id: str
    problem_order_index: int
    asset_key: str
    sections: tuple[str, ...]
    expected_vertices: int

    @property
    def stable_key(self) -> str:
        """Return the problem-target identity used in logs and manifests."""

        return f"{self.problem_id}:{self.asset_key}"


@dataclass
class GroupInventory:
    """Record compact counts and the exact PNG candidates for one group."""

    theme_title: str
    snapshot_theme_id: str
    source_group_id: str
    group_key: str
    group_order_index: int
    counts: dict[str, int]
    non_svg_content_types: dict[str, int]
    png_problem_ids: list[str]
    png_source_problem_ids: list[str]
    candidates: list[AssetCandidate] = field(repr=False)

    def manifest_payload(self) -> dict[str, Any]:
        """Return a JSON-safe inventory payload with stable candidate identities."""

        payload = asdict(self)
        payload["candidates"] = [asdict(candidate) for candidate in self.candidates]
        return payload


@dataclass(frozen=True)
class RefreshedAsset:
    """Hold the exact current PNG state read immediately before work."""

    transformation_target_id: str
    asset: dict[str, Any]
    replacement_context: dict[str, Any]


@dataclass(frozen=True)
class PreparedAsset:
    """Hold one validated local SVG pending an optional MCP upload."""

    candidate: AssetCandidate
    transformation_target_id: str
    input_sha256: str
    input_size_bytes: int
    output_sha256: str
    output_size_bytes: int
    canonical_asset_key: str
    alt_text: str
    input_path: Path
    svg_path: Path
    diagnostic_path: Path
    validation: dict[str, Any]


@dataclass(frozen=True)
class RollbackCandidate:
    """Identify one exact applied SourceAsset transformation to remove safely."""

    candidate: AssetCandidate
    transformation_target_id: str
    source_asset_id: str
    output_sha256: str


@dataclass(frozen=True)
class _CandidateOutcome:
    """Carry one isolated asset result back to deterministic accounting."""

    candidate: AssetCandidate
    status: str
    stage: str
    prepared: PreparedAsset | None = None
    source_asset_id: str | None = None
    cleanup: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class _DeterminismGate:
    """Verify exactly the first accepted render before any worker applies it."""

    converter: Any
    template_path: Path
    run_dir: Path
    logger: EventLogger | None = None
    verified: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

    def verify(self, prepared: PreparedAsset, logger: EventLogger) -> None:
        """Serialize the first repeat render and release later accepted assets."""

        with self.lock:
            if self.verified:
                return
            verify_first_deterministic_render(
                prepared,
                converter=self.converter,
                template_path=self.template_path,
                run_dir=self.run_dir,
            )
            self.verified = True
            logger.emit(
                "determinism_verified",
                source_problem_id=prepared.candidate.source_problem_id,
                asset_key=prepared.candidate.asset_key,
                output_sha256=prepared.output_sha256,
            )


@dataclass(frozen=True)
class _ProcessingContext:
    """Share immutable candidate dependencies across bounded worker threads."""

    client: McpClient
    source_site_id: str
    converter: Any
    converter_fingerprint: str
    template_path: Path
    run_dir: Path
    transfer_timeout_seconds: float
    logger: EventLogger
    apply: bool
    determinism_gate: _DeterminismGate


class EventLogger:
    """Write flush-on-event JSONL plus compact human-readable stdout lines."""

    def __init__(self, path: Path, *, color: str = "auto") -> None:
        """Open an append-only log at *path*."""

        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._stream = path.open("a", encoding="utf-8")
        self._lock = threading.RLock()
        self._color = color == "always" or (
            color == "auto" and sys.stdout.isatty() and "NO_COLOR" not in os.environ
        )

    def close(self) -> None:
        """Flush and close the event stream."""

        with self._lock:
            self._stream.flush()
            self._stream.close()

    def emit(self, event: str, *, level: str = "info", **fields: Any) -> None:
        """Persist one structured event and mirror its key fields to stdout."""

        with self._lock:
            self._emit_unlocked(event, level=level, **fields)

    def _emit_unlocked(
        self,
        event: str,
        *,
        level: str = "info",
        **fields: Any,
    ) -> None:
        """Write one event while the logger lock is held."""

        payload = {
            "at": datetime.now(UTC).isoformat(),
            "level": level,
            "event": event,
            **fields,
        }
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        self._stream.write(line + "\n")
        self._stream.flush()
        prefix = payload["at"][11:19]
        if event == "worklist_group_scan_start":
            position = int(fields.get("position") or 0)
            total = int(fields.get("total_groups") or 0)
            theme = str(fields.get("theme") or "unknown theme")
            group_key = str(fields.get("group_key") or "unknown")
            message = f"СКАНИРУЮ ГРУППУ {position}/{total}  {theme} / {group_key}"
            print(
                f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_CYAN)}",
                flush=True,
            )
            return
        if event == "worklist_group_scanned":
            position = int(fields.get("position") or 0)
            total = int(fields.get("total_groups") or 0)
            theme = str(fields.get("theme") or "unknown theme")
            group_key = str(fields.get("group_key") or "unknown")
            tasks = int(fields.get("tasks") or 0)
            message = (
                f"ГРУППА ПРОСКАНИРОВАНА {position}/{total}  "
                f"{theme} / {group_key}  ЦЕЛЕЙ {tasks}"
            )
            print(
                f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_GREEN)}",
                flush=True,
            )
            return
        if event == "worklist_ready":
            groups = int(fields.get("groups") or 0)
            tasks = int(fields.get("tasks") or 0)
            message = f"СПИСОК ЦЕЛЕЙ ГОТОВ  ГРУПП {groups}  ЗАДАЧ {tasks}"
            print(
                f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_BRIGHT_GREEN)}",
                flush=True,
            )
            return
        if event == "resume_ready":
            tasks = int(fields.get("tasks") or 0)
            applied = int(fields.get("applied") or 0)
            missing = int(fields.get("missing") or 0)
            rejected = int(fields.get("rejected") or 0)
            message = (
                f"ВОЗОБНОВЛЕНИЕ: ОСТАЛОСЬ {tasks}  "
                f"ГОТОВЫХ ПРОПУЩЕНО {applied}  "
                f"НЕТ ФАЙЛА {missing}  REJECTED {rejected}"
            )
            print(
                f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_BRIGHT_GREEN)}",
                flush=True,
            )
            return
        if event == "rollback_ready":
            tasks = int(fields.get("tasks") or 0)
            message = f"ROLLBACK ГОТОВ  ТОЧНЫХ ЦЕЛЕЙ {tasks}"
            print(
                f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_RED)}",
                flush=True,
            )
            return
        if event == "group_transition":
            theme = str(fields.get("theme") or "unknown theme")
            group_key = str(fields.get("group_key") or "unknown")
            message = f"ПЕРЕХОЖУ К ГРУППЕ {theme} / {group_key}"
            print(
                f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_RED)}",
                flush=True,
            )
            return
        if event == "group_opened":
            tasks = int(fields.get("tasks") or 0)
            message = f"ГРУППА ОТКРЫТА, ЦЕЛЕЙ {tasks}"
            print(
                f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_RED)}",
                flush=True,
            )
            return
        if event in TASK_STAGE_STYLES and fields.get("source_problem_id"):
            label, stage_color = TASK_STAGE_STYLES[event]
            theme = str(fields.get("theme") or "unknown theme")
            group_key = str(fields.get("group_key") or "unknown")
            source_problem_id = str(fields["source_problem_id"])
            group_text = self._paint(
                f"{theme} / group {group_key}", ANSI_BOLD + ANSI_CYAN
            )
            task_text = self._paint(
                f"Task {source_problem_id}", ANSI_BOLD + ANSI_YELLOW
            )
            stage_text = self._paint(label, ANSI_BOLD + stage_color)
            detail = ""
            if event in {
                "asset_rejected",
                "asset_stale",
                "asset_error",
                "rollback_stale",
            }:
                reason = str(fields.get("reason") or "")
                detail = f"  {reason}" if reason else ""
            print(
                f"{prefix}  {group_text}  {task_text}  {stage_text}{detail}",
                flush=True,
            )
            return
        if event == "batch_start":
            batch = int(fields.get("batch") or 0)
            tasks = int(fields.get("tasks") or 0)
            message = f"ПАКЕТ {batch}  ЗАДАЧ {tasks}"
            print(f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_BLUE)}", flush=True)
            return
        if event == "worker_pool_start":
            tasks = int(fields.get("tasks") or 0)
            workers = int(fields.get("max_workers") or 0)
            message = f"ОКНО ЗАПУЩЕНО  ЗАДАЧ {tasks}  ПАРАЛЛЕЛЬНО {workers}"
            print(f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_BLUE)}", flush=True)
            return
        if event == "batch_complete":
            batch = int(fields.get("batch") or 0)
            prepared = int(fields.get("prepared") or 0)
            replaced = int(fields.get("replaced") or 0)
            rolled_back = int(fields.get("rolled_back") or 0)
            if "rolled_back" in fields:
                message = f"ПАКЕТ {batch} ЗАВЕРШЁН  ОТКАЧЕНО {rolled_back}"
            else:
                message = (
                    f"ПАКЕТ {batch} ЗАВЕРШЁН  "
                    f"ПЕРЕФОРМАТИРОВАНО {prepared}  ПРИМЕНЕНО {replaced}"
                )
            print(f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_GREEN)}", flush=True)
            return
        if event == "batch_pause":
            seconds = fields.get("seconds") or 0
            message = f"ПАУЗА {seconds} СЕК."
            print(f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_YELLOW)}", flush=True)
            return
        if event == "run_complete":
            status = str(fields.get("status") or "completed")
            if "assets_rolled_back" in fields:
                rolled_back = int(fields.get("assets_rolled_back") or 0)
                errors = int(fields.get("asset_errors") or 0)
                message = (
                    f"ROLLBACK ГОТОВ  {status}  ОТКАЧЕНО {rolled_back}  "
                    f"ОШИБОК {errors}"
                )
                print(
                    f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_BRIGHT_GREEN)}",
                    flush=True,
                )
                return
            replaced = int(fields.get("assets_replaced") or 0)
            rejected = int(fields.get("assets_rejected") or 0)
            errors = int(fields.get("asset_errors") or 0)
            message = (
                f"ГОТОВО  {status}  ПРИМЕНЕНО {replaced}  "
                f"ОТКЛОНЕНО {rejected}  ОШИБОК {errors}"
            )
            print(
                f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_BRIGHT_GREEN)}",
                flush=True,
            )
            return
        if event == "run_failed" or level.lower() == "error":
            reason = str(fields.get("reason") or event)
            message = f"ОШИБКА  {reason}"
            print(f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_RED)}", flush=True)

    def _paint(self, text: str, style: str) -> str:
        """Wrap text in ANSI style codes when color output is enabled."""

        return f"{style}{text}{ANSI_RESET}" if self._color else text


class McpClient:
    """Call the stateless TeacherHelper Streamable HTTP JSON-RPC endpoint."""

    def __init__(
        self,
        *,
        url: str,
        api_key: str,
        timeout_seconds: float,
        logger: EventLogger,
    ) -> None:
        """Create an authenticated MCP client without logging its bearer token."""

        self.url = url
        self.logger = logger
        self._next_id = 0
        self._id_lock = threading.Lock()
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout_seconds),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
            },
        )

    def close(self) -> None:
        """Close the shared authenticated HTTP connection pool."""

        self._client.close()

    def call(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        attempts: int = 3,
    ) -> dict[str, Any]:
        """Call one MCP tool, retrying only with the same idempotent arguments."""

        arguments = arguments or {}
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            with self._id_lock:
                self._next_id += 1
                request_id = self._next_id
            payload = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
            try:
                response = self._client.post(self.url, json=payload)
                response.raise_for_status()
                envelope = response.json()
                if not isinstance(envelope, dict):
                    raise McpCallError("MCP response is not a JSON object")
                if envelope.get("error"):
                    raise McpCallError(_compact_error(envelope["error"]))
                result = envelope.get("result")
                if not isinstance(result, dict):
                    raise McpCallError("MCP response has no result object")
                if result.get("isError"):
                    raise McpCallError(_mcp_content_text(result) or "MCP tool failed")
                return _unpack_mcp_result(result)
            except (httpx.HTTPError, ValueError, McpCallError) as exc:
                last_error = exc
                if attempt >= attempts:
                    break
                delay = float(attempt)
                self.logger.emit(
                    "mcp_retry",
                    level="warning",
                    tool=name,
                    attempt=attempt,
                    delay_seconds=delay,
                    reason=_safe_exception(exc),
                )
                time.sleep(delay)
        raise McpCallError(
            f"{name} failed after {attempts} attempt(s): {_safe_exception(last_error)}"
        ) from last_error


def _compact_error(value: Any) -> str:
    """Return a bounded JSON error string."""

    return json.dumps(value, ensure_ascii=False, default=str)[:1000]


def _safe_exception(exc: BaseException | None) -> str:
    """Return a bounded one-line exception message suitable for logs."""

    if exc is None:
        return "unknown_error"
    return " ".join(str(exc).split())[:1000]


def _mcp_content_text(result: dict[str, Any]) -> str:
    """Join text blocks from one MCP CallToolResult."""

    return "\n".join(
        str(block.get("text") or "")
        for block in result.get("content", [])
        if isinstance(block, dict) and block.get("type") == "text"
    ).strip()


def _unpack_mcp_result(result: dict[str, Any]) -> dict[str, Any]:
    """Extract the structured payload returned by a TeacherHelper MCP tool."""

    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    for block in result.get("content", []):
        if not isinstance(block, dict) or block.get("type") != "text":
            continue
        text = str(block.get("text") or "").strip()
        if not text:
            continue
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            return decoded
    raise McpCallError("MCP tool returned no structured JSON payload")


def _chunks(values: Sequence[str], size: int) -> Iterator[list[str]]:
    """Yield stable fixed-size list chunks."""

    for start in range(0, len(values), size):
        yield list(values[start : start + size])


def _bounded_map_ordered(
    values: Sequence[_T],
    worker: Callable[[_T], _R],
    *,
    max_workers: int,
) -> tuple[_R, ...]:
    """Run a sliding worker window and return results in input order."""

    if max_workers <= 0:
        raise ValueError("max_workers must be positive")
    if max_workers == 1 or len(values) <= 1:
        return tuple(map(worker, values))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return tuple(executor.map(worker, values))


def _sha256_bytes(data: bytes) -> str:
    """Return the lowercase SHA-256 digest for *data*."""

    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    """Return the lowercase SHA-256 digest for one local file."""

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Replace one local JSON checkpoint atomically."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _normalized_content_type(value: Any) -> str:
    """Normalize an optional media type without parameters."""

    return str(value or "").split(";", 1)[0].strip().lower()


def _validate_startup(client: McpClient, *, mode: str, logger: EventLogger) -> str:
    """Verify identity, scopes, role, and all required MCP tools."""

    writes = mode in {"apply", "rollback"}
    info = client.call("mcp_server_info", attempts=3)
    scopes = {str(scope) for scope in info.get("effective_scopes", info.get("scopes", []))}
    required_scopes = {"source_content:read", "source_groups:read"}
    if writes:
        required_scopes.add("source_content:write")
    missing_scopes = sorted(required_scopes - scopes)
    if missing_scopes:
        raise PipelineError(f"MCP credential lacks scopes: {missing_scopes}")

    capabilities = client.call("get_mcp_capabilities", attempts=3)
    usable = {
        str(item.get("name"))
        for item in capabilities.get("usable_tools", [])
        if isinstance(item, dict) and item.get("usable") is True
    }
    required_tools = (
        REQUIRED_ROLLBACK_MCP_TOOLS if mode == "rollback" else REQUIRED_MCP_TOOLS
    )
    missing_tools = sorted(required_tools - usable)
    if missing_tools:
        raise PipelineError(f"MCP tools are unavailable: {missing_tools}")
    if writes and str(capabilities.get("role") or "") != "admin":
        raise PipelineError(f"{mode} mode requires an admin MCP identity")
    user_id = str(info.get("user_id") or "")
    if not user_id:
        raise PipelineError("mcp_server_info returned no user_id")
    logger.emit(
        "mcp_ready",
        user_id=user_id,
        role=capabilities.get("role"),
        scopes=sorted(scopes),
        mode=mode,
    )
    return user_id


def discover_catalog_scope(
    client: McpClient,
    *,
    catalog_snapshot_id: str,
    category_key: str,
    category_title: str,
    theme_titles: Sequence[str],
    group_keys: Sequence[str] | None = None,
    logger: EventLogger,
) -> tuple[str, list[tuple[ThemeScope, list[GroupScope]]]]:
    """Build the immutable production scope without reading the catalog tree."""

    del client
    if catalog_snapshot_id != DEFAULT_CATALOG_SNAPSHOT_ID:
        raise PipelineError("fixed theme UUIDs require the configured catalog snapshot")
    if category_key != DEFAULT_CATEGORY_KEY or category_title != DEFAULT_CATEGORY_TITLE:
        raise PipelineError("fixed theme UUIDs require the configured category")
    if len(set(theme_titles)) != len(theme_titles):
        raise PipelineError("target theme titles must be unique")

    requested_group_keys = set(group_keys or [])
    scope: list[tuple[ThemeScope, list[GroupScope]]] = []
    all_group_ids: set[str] = set()
    for requested_title in theme_titles:
        config = FIXED_THEME_CONFIG.get(requested_title)
        if config is None:
            raise PipelineError(f"no fixed UUID configuration for theme {requested_title!r}")
        theme = ThemeScope(
            title=requested_title,
            snapshot_theme_id=str(config["snapshot_theme_id"]),
            source_theme_id=str(config["source_theme_id"]),
            order_index=int(config["order_index"]),
            source_groups_count=int(config["source_groups_count"]),
            expected_vertices=EXPECTED_VERTICES_BY_THEME[requested_title],
        )
        configured_groups = FIXED_SOURCE_GROUPS.get(requested_title)
        if configured_groups is None:
            raise PipelineError(f"no fixed source groups for theme {theme.title!r}")
        if len(configured_groups) != theme.source_groups_count:
            raise PipelineError(
                f"theme {theme.title!r} declares {theme.source_groups_count} groups "
                f"but fixes {len(configured_groups)}"
            )
        groups: list[GroupScope] = []
        seen_group_keys: set[str] = set()
        for order_index, (group_id, group_key) in enumerate(configured_groups):
            if not group_id or group_id in all_group_ids:
                raise PipelineError(f"theme {theme.title!r} has a missing/duplicate group id")
            if not group_key or group_key in seen_group_keys:
                raise PipelineError(f"theme {theme.title!r} has a missing/duplicate group key")
            all_group_ids.add(group_id)
            seen_group_keys.add(group_key)
            groups.append(
                GroupScope(
                    source_group_id=group_id,
                    group_key=group_key,
                    order_index=order_index,
                )
            )
        selected_groups = [
            group for group in groups
            if not requested_group_keys or group.group_key in requested_group_keys
        ]
        if not selected_groups:
            continue
        logger.emit(
            "theme_scope_loaded",
            theme=theme.title,
            snapshot_theme_id=theme.snapshot_theme_id,
            groups=len(selected_groups),
        )
        scope.append((theme, selected_groups))
    selected_group_keys = {
        group.group_key for _theme, groups in scope for group in groups
    }
    missing_group_keys = sorted(requested_group_keys - selected_group_keys)
    if missing_group_keys:
        raise PipelineError(
            f"group keys are outside the selected fixed themes: {missing_group_keys}"
        )
    return DEFAULT_SOURCE_SITE_ID, scope


def _load_group_targets(
    client: McpClient,
    *,
    catalog_snapshot_id: str,
    group: GroupScope,
    source_problem_ids: Sequence[str],
) -> dict[str, dict[str, Any]]:
    """Resolve current problem UUIDs and Normalized status for one exact group."""

    del catalog_snapshot_id
    ordered_source_problem_ids = list(
        dict.fromkeys(str(value).strip() for value in source_problem_ids if str(value).strip())
    )
    targets_by_source_problem_id: dict[str, dict[str, Any]] = {}
    children = client.call(
        "get_source_catalog_children",
        {"parent_id": group.source_group_id, "parent_type": "group"},
    )
    children_by_source_problem_id: dict[str, tuple[int, str]] = {}
    for order_index, item in enumerate(children.get("items", [])):
        if not isinstance(item, dict):
            continue
        problem_id = str(item.get("uuid") or "")
        name = str(item.get("name") or "")
        prefix = "Задача "
        if not problem_id or not name.startswith(prefix):
            raise PipelineError("group child has no canonical problem UUID/source id")
        source_problem_id = name[len(prefix) :].strip()
        if not source_problem_id or source_problem_id in children_by_source_problem_id:
            raise PipelineError("group children contain a missing/duplicate source problem id")
        children_by_source_problem_id[source_problem_id] = (order_index, problem_id)

    for source_problem_id in ordered_source_problem_ids:
        child = children_by_source_problem_id.get(source_problem_id)
        if child is None:
            continue
        order_index, problem_id = child
        state = client.call("get_problem_pipeline_state", {"problem_id": problem_id})
        statuses = state.get("statuses")
        normalized_status = (
            str(statuses.get("normalized") or "")
            if isinstance(statuses, dict)
            else ""
        )
        targets_by_source_problem_id[source_problem_id] = {
            "source_group_id": group.source_group_id,
            "problem_id": problem_id,
            "source_problem_id": source_problem_id,
            "order_index": order_index,
            "source_group_status": "processing",
            "problem_source_content_status": normalized_status,
            "has_normalized_content": normalized_status in {"ready", "rejected"},
        }
    return targets_by_source_problem_id


def build_group_inventory(
    client: McpClient,
    *,
    catalog_snapshot_id: str,
    theme: ThemeScope,
    group: GroupScope,
) -> GroupInventory:
    """Select every current ordinary PNG from non-rejected normalized problems."""

    images_payload = client.call(
        "get_source_catalog_section_images",
        {"target_id": group.source_group_id, "target_type": "group"},
    )
    returned_scope = images_payload.get("scope")
    if not isinstance(returned_scope, dict):
        raise PipelineError("section-image response has no exact scope")
    if str(returned_scope.get("catalog_snapshot_id") or "") != catalog_snapshot_id:
        raise PipelineError("section-image response escaped the fixed catalog")
    returned_group_ids = {
        str(value) for value in returned_scope.get("source_group_ids", [])
    }
    if returned_group_ids != {group.source_group_id}:
        raise PipelineError("section-image response escaped the fixed source group")
    try:
        concrete_problem_count = int(images_payload["concrete_problem_count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PipelineError("section-image response has no concrete problem count") from exc
    if concrete_problem_count < 0:
        raise PipelineError("section-image response has a negative problem count")

    images_by_source_problem: dict[str, dict[tuple[str, str, str], set[str]]] = {}
    for section in ("condition", "solution"):
        section_payload = images_payload.get(section, {})
        problems = (
            section_payload.get("problems", [])
            if isinstance(section_payload, dict)
            else []
        )
        for problem in problems:
            if not isinstance(problem, dict):
                continue
            source_problem_id = str(problem.get("source_problem_id") or "")
            if not source_problem_id:
                raise PipelineError("section-image response contains an empty source problem id")
            bucket = images_by_source_problem.setdefault(source_problem_id, {})
            for image in problem.get("images", []):
                if not isinstance(image, dict):
                    continue
                identity = (
                    str(image.get("asset_key") or ""),
                    str(image.get("kind") or ""),
                    _normalized_content_type(image.get("content_type")),
                )
                if identity[0]:
                    bucket.setdefault(identity, set()).add(section)

    ordinary_image_source_problem_ids = sorted(
        (
            source_problem_id
            for source_problem_id, image_rows in images_by_source_problem.items()
            if any(kind == "ordinary_image" for _, kind, _ in image_rows)
        ),
        key=lambda value: (len(value), value),
    )
    targets = _load_group_targets(
        client,
        catalog_snapshot_id=catalog_snapshot_id,
        group=group,
        source_problem_ids=ordinary_image_source_problem_ids,
    )

    counts: Counter[str] = Counter(total_group_items=concrete_problem_count)
    content_types: Counter[str] = Counter()
    candidates: list[AssetCandidate] = []
    png_problem_ids: set[str] = set()
    png_source_problem_ids: set[str] = set()
    for source_problem_id in ordinary_image_source_problem_ids:
        target = targets.get(source_problem_id)
        if target is None:
            counts["missing_parser_target"] += 1
            continue
        problem_id = str(target.get("problem_id") or "")
        counts["parser_targets"] += 1
        group_status = str(target.get("source_group_status") or "")
        problem_status = str(target.get("problem_source_content_status") or "")
        if group_status == "rejected":
            raise PipelineError(
                f"configured source group {group.source_group_id} is unexpectedly rejected"
            )
        if problem_status == "rejected":
            counts["rejected_problems"] += 1
            continue
        if target.get("has_normalized_content") is not True:
            counts["without_normalized_content"] += 1
            continue
        counts["eligible_problems"] += 1
        image_rows = images_by_source_problem.get(source_problem_id, {})
        for (asset_key, kind, content_type), sections in sorted(image_rows.items()):
            counts["all_section_images"] += 1
            if kind != "ordinary_image":
                counts["formula_or_unknown_images"] += 1
                continue
            counts["ordinary_images"] += 1
            if content_type == SVG_CONTENT_TYPE:
                counts["ordinary_svg_assets"] += 1
                continue
            counts["ordinary_non_svg_assets"] += 1
            content_types[content_type or "unknown"] += 1
            if content_type not in RASTER_CONTENT_TYPES:
                counts["ordinary_non_png_assets"] += 1
                continue
            counts["png_assets"] += 1
            png_problem_ids.add(problem_id)
            png_source_problem_ids.add(source_problem_id)
            candidates.append(
                AssetCandidate(
                    theme_title=theme.title,
                    snapshot_theme_id=theme.snapshot_theme_id,
                    theme_order_index=theme.order_index,
                    source_group_id=group.source_group_id,
                    group_key=group.group_key,
                    group_order_index=group.order_index,
                    problem_id=problem_id,
                    source_problem_id=source_problem_id,
                    problem_order_index=int(target.get("order_index") or 0),
                    asset_key=asset_key,
                    sections=tuple(sorted(sections)),
                    expected_vertices=theme.expected_vertices,
                )
            )
    escaped_source_problem_ids = set(targets) - set(ordinary_image_source_problem_ids)
    if escaped_source_problem_ids:
        raise PipelineError(
            "parser targets escaped requested source problems: "
            f"{sorted(escaped_source_problem_ids)[:3]}"
        )
    candidates.sort(
        key=lambda item: (
            item.problem_order_index,
            item.source_problem_id,
            item.asset_key,
        )
    )
    counts["png_tasks"] = len(png_problem_ids)
    counts.setdefault("png_assets", 0)
    return GroupInventory(
        theme_title=theme.title,
        snapshot_theme_id=theme.snapshot_theme_id,
        source_group_id=group.source_group_id,
        group_key=group.group_key,
        group_order_index=group.order_index,
        counts=dict(sorted(counts.items())),
        non_svg_content_types=dict(sorted(content_types.items())),
        png_problem_ids=sorted(png_problem_ids),
        png_source_problem_ids=sorted(
            png_source_problem_ids,
            key=lambda value: (len(value), value),
        ),
        candidates=candidates,
    )


def _current_asset_for_candidate(
    context: dict[str, Any], candidate: AssetCandidate
) -> dict[str, Any]:
    """Return the unique current normalized asset matching one candidate."""

    normalized = context.get("normalized_content")
    assets = normalized.get("assets", []) if isinstance(normalized, dict) else []
    matches = [
        asset
        for asset in assets
        if isinstance(asset, dict)
        and str(asset.get("asset_key") or "") == candidate.asset_key
        and str(asset.get("kind") or "") == "ordinary_image"
    ]
    if len(matches) != 1:
        raise CandidateStale(
            f"expected one current ordinary asset, found {len(matches)}"
        )
    return matches[0]


def refresh_candidate(client: McpClient, candidate: AssetCandidate) -> RefreshedAsset:
    """Re-read one candidate and its exact replacement decision context."""

    transformation_context = client.call(
        "get_problem_transformation_context",
        {"problem_id": candidate.problem_id},
    )
    asset = _current_asset_for_candidate(transformation_context, candidate)
    content_type = _normalized_content_type(asset.get("content_type"))
    if content_type and content_type not in RASTER_CONTENT_TYPES:
        raise CandidateStale(
            f"current content_type is {content_type or 'missing'}, not a supported raster"
        )
    target_id = str(asset.get("transformation_target_id") or "")
    if not target_id:
        raise CandidateStale("current PNG has no transformation_target_id")
    replacement_context = client.call(
        "get_problem_asset_target_context",
        {
            "problem_id": candidate.problem_id,
            "transformation_target_id": target_id,
        },
    )
    current_asset = replacement_context.get("current_asset")
    if not isinstance(current_asset, dict):
        raise CandidateStale("replacement context has no current_asset")
    if str(current_asset.get("asset_key") or "") != candidate.asset_key:
        raise CandidateStale("replacement context resolved another asset_key")
    replacement_content_type = _normalized_content_type(current_asset.get("content_type"))
    if replacement_content_type and replacement_content_type not in RASTER_CONTENT_TYPES:
        raise CandidateStale("replacement context no longer points to a supported raster")
    if str(replacement_context.get("transformation_target_id") or "") != target_id:
        raise CandidateStale("replacement target changed during re-read")
    return RefreshedAsset(
        transformation_target_id=target_id,
        asset=current_asset,
        replacement_context=replacement_context,
    )


def _transfer_get(contract: dict[str, Any], *, timeout_seconds: float) -> bytes:
    """Execute one capability-bound GET with only the returned headers."""

    if str(contract.get("method")) != "GET":
        raise PipelineError("download contract method is not GET")
    url = str(contract.get("download_url") or "")
    headers = contract.get("headers")
    if not url or not isinstance(headers, dict):
        raise PipelineError("download contract is incomplete")
    with httpx.Client(timeout=httpx.Timeout(timeout_seconds), follow_redirects=False) as client:
        response = client.get(url, headers={str(k): str(v) for k, v in headers.items()})
        response.raise_for_status()
        return response.content


def _transfer_put(
    contract: dict[str, Any], data: bytes, *, timeout_seconds: float
) -> dict[str, Any]:
    """Execute one capability-bound raw PUT with only the returned headers."""

    if str(contract.get("method")) != "PUT":
        raise PipelineError("upload contract method is not PUT")
    url = str(contract.get("upload_url") or "")
    headers = contract.get("headers")
    if not url or not isinstance(headers, dict) or not headers:
        raise PipelineError("upload contract is incomplete")
    with httpx.Client(timeout=httpx.Timeout(timeout_seconds), follow_redirects=False) as client:
        response = client.put(
            url,
            headers={str(k): str(v) for k, v in headers.items()},
            content=data,
        )
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise PipelineError("source asset upload returned no JSON object")
    return payload


def _validate_png(data: bytes, contract: dict[str, Any]) -> tuple[str, tuple[int, int]]:
    """Validate one supported raster, including historical MIME mismatches."""

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        expected_format = "PNG"
    elif data.startswith(b"\xff\xd8\xff"):
        expected_format = "JPEG"
    elif data.startswith(b"BM"):
        expected_format = "BMP"
    else:
        raise CandidateRejected("downloaded bytes are not a supported PNG/JPEG/BMP raster")
    digest = _sha256_bytes(data)
    expected_digest = str(contract.get("sha256") or "").lower()
    if expected_digest and digest != expected_digest:
        raise CandidateRejected("downloaded raster sha256 differs from MCP metadata")
    expected_size = contract.get("size_bytes")
    if expected_size is not None and int(expected_size) != len(data):
        raise CandidateRejected("downloaded raster size differs from MCP metadata")
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.format != expected_format:
                raise CandidateRejected(
                    f"Pillow decoded {image.format}, not {expected_format}"
                )
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
    except CandidateRejected:
        raise
    except Exception as exc:  # noqa: BLE001 - decoder failures are input rejections.
        raise CandidateRejected(f"invalid raster: {_safe_exception(exc)}") from exc
    if width <= 0 or height <= 0:
        raise CandidateRejected("raster has invalid dimensions")
    return digest, (width, height)


def _load_converter(converter_path: Path) -> Any:
    """Load the exact converter file selected for this process."""

    spec = importlib.util.spec_from_file_location("grid_png_converter_locked", converter_path)
    if spec is None or spec.loader is None:
        raise PipelineError(f"cannot import converter: {converter_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "run", None)):
        raise PipelineError("converter module has no callable run function")
    return module


def _parse_diagnostics(path: Path) -> dict[str, Any]:
    """Parse the converter's key=value diagnostics using safe literals."""

    if not path.is_file():
        raise CandidateRejected("converter did not create diagnostics")
    parsed: dict[str, Any] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        key, separator, raw_value = raw_line.partition("=")
        if not separator:
            continue
        key = key.strip()
        value = raw_value.strip()
        try:
            parsed[key] = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            try:
                parsed[key] = float(value)
            except ValueError:
                parsed[key] = value
    return parsed


def _polygon_area(points: Sequence[tuple[float, float]]) -> float:
    """Return the absolute shoelace area of one simple polygon."""

    return abs(
        sum(
            x1 * y2 - x2 * y1
            for (x1, y1), (x2, y2) in zip(points, (*points[1:], points[0]))
        )
    ) / 2.0


def _validate_diagnostics(
    diagnostics: dict[str, Any], *, theme_title: str, expected_vertices: int
) -> dict[str, Any]:
    """Fail closed when detected lattice or polygon invariants are implausible."""

    required = {
        "grid_source",
        "alpha_grid_x_step",
        "alpha_grid_y_step",
        "source_quad_before_snap",
        "source_quad_on_alpha_grid",
        "source_polygon_points",
        "grid_indices",
        "svg_size",
    }
    missing = sorted(required - diagnostics.keys())
    if missing:
        raise CandidateRejected(f"diagnostics are missing fields: {missing}")
    points_raw = diagnostics["source_polygon_points"]
    if not isinstance(points_raw, (list, tuple)):
        raise CandidateRejected("source_polygon_points is not a list")
    points = [tuple(map(int, point)) for point in points_raw]
    if len(points) != expected_vertices:
        raise CandidateRejected(
            f"detected {len(points)} vertices; theme requires {expected_vertices}"
        )
    if len(set(points)) != len(points):
        raise CandidateRejected("detected polygon has duplicate vertices")
    x_step = float(diagnostics["alpha_grid_x_step"])
    y_step = float(diagnostics["alpha_grid_y_step"])
    if min(x_step, y_step) <= 0:
        raise CandidateRejected("detected grid step is not positive")
    step_ratio = max(x_step, y_step) / min(x_step, y_step)
    if step_ratio > 1.18:
        raise CandidateRejected(f"square-grid step ratio is too large: {step_ratio:.4f}")

    before = diagnostics["source_quad_before_snap"]
    snapped = diagnostics["source_quad_on_alpha_grid"]
    if len(before) != expected_vertices or len(snapped) != expected_vertices:
        raise CandidateRejected("snap diagnostics have the wrong vertex count")
    normalized_offsets = [
        max(abs(float(x1) - float(x2)) / x_step, abs(float(y1) - float(y2)) / y_step)
        for (x1, y1), (x2, y2) in zip(before, snapped)
    ]
    max_snap_offset = max(normalized_offsets, default=0.0)
    if max_snap_offset > 0.45:
        raise CandidateRejected(
            f"polygon-to-grid snap offset is too large: {max_snap_offset:.4f} cell"
        )
    grid_indices_raw = diagnostics["grid_indices"]
    if not isinstance(grid_indices_raw, (list, tuple)):
        raise CandidateRejected("grid_indices is not a list")
    grid_indices = [tuple(map(int, point)) for point in grid_indices_raw]
    if len(grid_indices) != expected_vertices or len(set(grid_indices)) != len(grid_indices):
        raise CandidateRejected("ordered grid polygon has invalid vertices")
    area = _polygon_area(grid_indices)
    if area <= 0:
        raise CandidateRejected("detected polygon has zero area")
    if expected_vertices == 4:
        edges = [
            (
                grid_indices[(index + 1) % 4][0] - grid_indices[index][0],
                grid_indices[(index + 1) % 4][1] - grid_indices[index][1],
            )
            for index in range(4)
        ]
        if theme_title == "Трапеция":
            opposite_parallel = (
                edges[0][0] * edges[2][1] - edges[0][1] * edges[2][0] == 0
                or edges[1][0] * edges[3][1] - edges[1][1] * edges[3][0] == 0
            )
            if not opposite_parallel:
                raise CandidateRejected("detected quadrilateral is not a trapezoid")
        if theme_title == "Ромб":
            squared_lengths = [dx * dx + dy * dy for dx, dy in edges]
            if len(set(squared_lengths)) != 1:
                raise CandidateRejected("detected quadrilateral is not a rhombus")
    svg_size = diagnostics["svg_size"]
    if (
        not isinstance(svg_size, (list, tuple))
        or len(svg_size) != 2
        or min(float(svg_size[0]), float(svg_size[1])) <= 0
    ):
        raise CandidateRejected("generated SVG has invalid dimensions")
    return {
        "grid_source": str(diagnostics["grid_source"]),
        "grid_correction": str(diagnostics.get("grid_correction") or "none"),
        "vertices": points,
        "ordered_grid_vertices": grid_indices,
        "polygon_area_cells": area,
        "grid_step_ratio": step_ratio,
        "max_snap_offset_cells": max_snap_offset,
        "svg_size": list(svg_size),
    }


def _validate_svg(data: bytes, *, expected_vertices: int) -> None:
    """Validate generated SVG structure before server-side strict validation."""

    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise CandidateRejected(f"generated SVG is not valid XML: {exc}") from exc
    if root.tag.rsplit("}", 1)[-1].lower() != "svg":
        raise CandidateRejected("generated XML root is not svg")
    if not root.get("viewBox"):
        raise CandidateRejected("generated SVG has no viewBox")
    blocked_tags = {"script", "foreignobject", "iframe", "object", "embed"}
    polygons = []
    for element in root.iter():
        local_tag = element.tag.rsplit("}", 1)[-1].lower()
        if local_tag in blocked_tags:
            raise CandidateRejected(f"generated SVG contains blocked tag {local_tag}")
        for attribute, value in element.attrib.items():
            local_attribute = attribute.rsplit("}", 1)[-1].lower()
            lowered = str(value).strip().lower()
            if local_attribute.startswith("on"):
                raise CandidateRejected("generated SVG contains an event handler")
            if local_attribute in {"href", "src"} and lowered:
                raise CandidateRejected("generated SVG contains a resource reference")
            if "javascript:" in lowered:
                raise CandidateRejected("generated SVG contains a javascript URL")
        if local_tag == "polygon" and element.get("points"):
            polygons.append(element.get("points", ""))
    if not polygons:
        raise CandidateRejected("generated SVG contains no polygon")
    point_count = len(polygons[-1].replace(",", " ").split()) // 2
    if point_count != expected_vertices:
        raise CandidateRejected(
            f"generated SVG polygon has {point_count} points, expected {expected_vertices}"
        )


def _canonical_asset_key(output_sha256: str, converter_fingerprint: str) -> str:
    """Return a deterministic reusable source-asset key for exact SVG bytes."""

    return (
        f"{CONVERTER_PROFILE}-{converter_fingerprint[:12]}-{output_sha256[:48]}"
    )


def _polygon_alt_text(validation: dict[str, Any]) -> str:
    """Serialize validated lattice vertices as the exact image alt text."""

    vertices = validation.get("vertices")
    if not isinstance(vertices, list):
        raise CandidateRejected("validated polygon vertices are missing")
    return str([tuple(int(coordinate) for coordinate in point) for point in vertices])


def prepare_candidate(
    client: McpClient,
    *,
    candidate: AssetCandidate,
    converter: Any,
    converter_fingerprint: str,
    template_path: Path,
    run_dir: Path,
    transfer_timeout_seconds: float,
    logger: EventLogger,
) -> PreparedAsset:
    """Download, convert, and validate one current raster without MCP writes."""

    refreshed = refresh_candidate(client, candidate)
    current_asset_id = str(
        refreshed.replacement_context.get("current_asset_id")
        or refreshed.asset.get("asset_id")
        or ""
    )
    if not current_asset_id:
        raise CandidateStale("current raster has no asset_id")
    metadata = client.call("get_asset", {"asset_id": current_asset_id})
    file_contract = client.call("get_asset_file", {"asset_id": current_asset_id})
    contract = {
        **metadata,
        "method": "GET",
        "download_url": urljoin(
            str(getattr(client, "url", DEFAULT_MCP_URL)),
            str(file_contract.get("url") or ""),
        ),
        "headers": {},
    }
    content_type = _normalized_content_type(contract.get("content_type"))
    file_content_type = _normalized_content_type(file_contract.get("content_type"))
    if content_type not in RASTER_CONTENT_TYPES or file_content_type != content_type:
        raise CandidateStale(
            "download capability no longer describes the same supported raster"
        )
    try:
        data = _transfer_get(contract, timeout_seconds=transfer_timeout_seconds)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {404, 410}:
            raise CandidateStale(
                f"source raster is unavailable (HTTP {exc.response.status_code})"
            ) from exc
        raise
    input_sha256, dimensions = _validate_png(data, contract)
    current_sha = str(metadata.get("sha256") or "").lower()
    if current_sha and current_sha != input_sha256:
        raise CandidateStale("replacement context sha256 differs from downloaded PNG")
    logger.emit(
        "source_downloaded",
        theme=candidate.theme_title,
        group_key=candidate.group_key,
        source_problem_id=candidate.source_problem_id,
        problem_id=candidate.problem_id,
        asset_key=candidate.asset_key,
        input_sha256=input_sha256,
        size_bytes=len(data),
    )

    artifact_dir = (
        run_dir
        / "artifacts"
        / f"{candidate.theme_order_index:02d}-{candidate.snapshot_theme_id[:8]}"
        / f"{candidate.group_order_index:04d}-{candidate.source_group_id[:8]}"
        / f"{candidate.problem_order_index:05d}-{candidate.problem_id[:8]}"
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    safe_asset_key = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in candidate.asset_key
    )
    input_suffix = ".bmp" if content_type in BMP_CONTENT_TYPES else ".png"
    input_path = artifact_dir / (
        f"{candidate.source_problem_id}-{safe_asset_key}-{input_sha256[:12]}{input_suffix}"
    )
    input_path.write_bytes(data)

    converter_stdout = io.StringIO()
    try:
        svg_path = Path(
            converter.run(
                str(input_path),
                artifact_dir,
                2,
                0.97,
                20,
                1,
                1.5,
                True,
                None,
                template_path,
                False,
                expected_vertices=candidate.expected_vertices,
                output_stream=converter_stdout,
            )
        )
    except Exception as exc:  # noqa: BLE001 - converter failures reject only this input.
        raise CandidateRejected(f"converter failed: {_safe_exception(exc)}") from exc
    diagnostic_path = svg_path.with_suffix(".txt")
    diagnostics = _parse_diagnostics(diagnostic_path)
    validation = _validate_diagnostics(
        diagnostics,
        theme_title=candidate.theme_title,
        expected_vertices=candidate.expected_vertices,
    )
    svg_bytes = svg_path.read_bytes()
    _validate_svg(svg_bytes, expected_vertices=candidate.expected_vertices)
    output_sha256 = _sha256_bytes(svg_bytes)
    validation = {
        **validation,
        "input_dimensions": list(dimensions),
        "converter_stdout": converter_stdout.getvalue().strip().splitlines()[-4:],
    }
    alt_text = _polygon_alt_text(validation)
    return PreparedAsset(
        candidate=candidate,
        transformation_target_id=refreshed.transformation_target_id,
        input_sha256=input_sha256,
        input_size_bytes=len(data),
        output_sha256=output_sha256,
        output_size_bytes=len(svg_bytes),
        canonical_asset_key=_canonical_asset_key(output_sha256, converter_fingerprint),
        alt_text=alt_text,
        input_path=input_path,
        svg_path=svg_path,
        diagnostic_path=diagnostic_path,
        validation=validation,
    )


def verify_first_deterministic_render(
    prepared: PreparedAsset,
    *,
    converter: Any,
    template_path: Path,
    run_dir: Path,
) -> None:
    """Render the first accepted input twice and require byte-identical artifacts."""

    check_dir = run_dir / "determinism-check"
    check_dir.mkdir(parents=True, exist_ok=True)
    check_svg = Path(
        converter.run(
            str(prepared.input_path),
            check_dir,
            2,
            0.97,
            20,
            1,
            1.5,
            True,
            None,
            template_path,
            False,
            expected_vertices=prepared.candidate.expected_vertices,
            output_stream=io.StringIO(),
        )
    )
    if check_svg.read_bytes() != prepared.svg_path.read_bytes():
        raise PipelineError("converter produced different SVG bytes for the same PNG")
    if check_svg.with_suffix(".txt").read_bytes() != prepared.diagnostic_path.read_bytes():
        raise PipelineError("converter produced different diagnostics for the same PNG")


def _verify_source_asset(
    client: McpClient,
    *,
    source_asset_id: str,
    prepared: PreparedAsset,
) -> dict[str, Any]:
    """Re-read and verify one uploaded reusable source asset."""

    payload = client.call("get_source_asset", {"source_asset_id": source_asset_id})
    asset = payload.get("source_asset")
    if not isinstance(asset, dict):
        raise PipelineError("uploaded source asset cannot be re-read")
    if str(asset.get("id") or asset.get("source_asset_id") or "") != source_asset_id:
        raise PipelineError("get_source_asset returned another id")
    if str(asset.get("canonical_asset_key") or "") != prepared.canonical_asset_key:
        raise PipelineError("uploaded source asset has another canonical key")
    if _normalized_content_type(asset.get("content_type")) != SVG_CONTENT_TYPE:
        raise PipelineError("uploaded source asset is not SVG")
    if str(asset.get("sha256") or "").lower() != prepared.output_sha256:
        raise PipelineError("uploaded source asset sha256 differs from local SVG")
    return asset


def apply_prepared_asset(
    client: McpClient,
    *,
    source_site_id: str,
    prepared: PreparedAsset,
    transfer_timeout_seconds: float,
    logger: EventLogger,
) -> tuple[str, dict[str, Any]]:
    """Upload a worklist-bound SVG, replace its exact target, and verify readback."""

    svg_bytes = prepared.svg_path.read_bytes()
    if _sha256_bytes(svg_bytes) != prepared.output_sha256:
        raise PipelineError("local SVG changed after validation")
    upload_contract = client.call(
        "prepare_source_asset_upload",
        {
            "source_site_id": source_site_id,
            "canonical_asset_key": prepared.canonical_asset_key,
            "byte_size": len(svg_bytes),
            "sha256": prepared.output_sha256,
            "content_type": SVG_CONTENT_TYPE,
        },
    )
    logger.emit(
        "upload_link_created",
        theme=prepared.candidate.theme_title,
        group_key=prepared.candidate.group_key,
        source_problem_id=prepared.candidate.source_problem_id,
        problem_id=prepared.candidate.problem_id,
        asset_key=prepared.candidate.asset_key,
        canonical_asset_key=prepared.canonical_asset_key,
    )
    upload = _transfer_put(
        upload_contract,
        svg_bytes,
        timeout_seconds=transfer_timeout_seconds,
    )
    source_asset_id = str(upload.get("source_asset_id") or "")
    if not source_asset_id:
        raise PipelineError("source asset upload returned no source_asset_id")
    if str(upload.get("sha256") or "").lower() != prepared.output_sha256:
        raise PipelineError("source asset upload response has another sha256")
    _verify_source_asset(
        client,
        source_asset_id=source_asset_id,
        prepared=prepared,
    )
    logger.emit(
        "svg_uploaded",
        theme=prepared.candidate.theme_title,
        group_key=prepared.candidate.group_key,
        source_problem_id=prepared.candidate.source_problem_id,
        problem_id=prepared.candidate.problem_id,
        asset_key=prepared.candidate.asset_key,
        source_asset_id=source_asset_id,
        output_sha256=prepared.output_sha256,
    )

    replacement_result = client.call(
        "replace_problem_asset",
        {
            "problem_id": prepared.candidate.problem_id,
            "transformation_target_id": prepared.transformation_target_id,
            "replacement_asset_id": source_asset_id,
            "scope": "target",
            "alt_text": prepared.alt_text,
        },
        attempts=2,
    )
    readback = client.call(
        "get_problem_asset_target_context",
        {
            "problem_id": prepared.candidate.problem_id,
            "transformation_target_id": prepared.transformation_target_id,
        },
    )
    asset = readback.get("current_asset")
    if not isinstance(asset, dict):
        raise PipelineError("replacement readback has no current_asset")
    readback_asset_id = str(
        readback.get("current_asset_id") or asset.get("asset_id") or ""
    )
    if readback_asset_id != source_asset_id:
        raise PipelineError("replacement readback points to another asset_id")
    readback_metadata = client.call("get_asset", {"asset_id": readback_asset_id})
    if _normalized_content_type(readback_metadata.get("content_type")) != SVG_CONTENT_TYPE:
        raise PipelineError("replacement readback is not SVG")
    if str(readback_metadata.get("sha256") or "").lower() != prepared.output_sha256:
        raise PipelineError("replacement readback sha256 differs from uploaded SVG")
    if str(asset.get("alt") or "") != prepared.alt_text:
        raise PipelineError("replacement readback alt differs from polygon vertices")
    cleanup = {
        "cleanup_candidate_asset_id": replacement_result.get(
            "cleanup_candidate_asset_id"
        )
    }
    return source_asset_id, cleanup if isinstance(cleanup, dict) else {}


def _process_candidate(
    context: _ProcessingContext,
    candidate: AssetCandidate,
) -> _CandidateOutcome:
    """Prepare and optionally apply one asset as an isolated worker chain."""

    try:
        prepared = prepare_candidate(
            context.client,
            candidate=candidate,
            converter=context.converter,
            converter_fingerprint=context.converter_fingerprint,
            template_path=context.template_path,
            run_dir=context.run_dir,
            transfer_timeout_seconds=context.transfer_timeout_seconds,
            logger=context.logger,
        )
        context.determinism_gate.verify(prepared, context.logger)
        context.logger.emit(
            "asset_prepared",
            theme=candidate.theme_title,
            group_key=candidate.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            input_sha256=prepared.input_sha256,
            output_sha256=prepared.output_sha256,
            alt_text=prepared.alt_text,
            validation=prepared.validation,
            svg_path=str(prepared.svg_path),
        )
    except CandidateStale as exc:
        reason = _safe_exception(exc)
        context.logger.emit(
            "asset_stale",
            level="warning",
            theme=candidate.theme_title,
            group_key=candidate.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            stage="prepare",
            reason=reason,
        )
        return _CandidateOutcome(candidate, "stale", "prepare", error=reason)
    except CandidateRejected as exc:
        reason = _safe_exception(exc)
        context.logger.emit(
            "asset_rejected",
            level="warning",
            theme=candidate.theme_title,
            group_key=candidate.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            reason=reason,
        )
        return _CandidateOutcome(candidate, "rejected", "prepare", error=reason)
    except (McpCallError, httpx.HTTPError, OSError) as exc:
        reason = _safe_exception(exc)
        context.logger.emit(
            "asset_error",
            level="error",
            theme=candidate.theme_title,
            group_key=candidate.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            stage="prepare",
            reason=reason,
        )
        return _CandidateOutcome(candidate, "error", "prepare", error=reason)

    if not context.apply:
        return _CandidateOutcome(
            candidate,
            "dry_run",
            "prepare",
            prepared=prepared,
        )
    try:
        source_asset_id, cleanup = apply_prepared_asset(
            context.client,
            source_site_id=context.source_site_id,
            prepared=prepared,
            transfer_timeout_seconds=context.transfer_timeout_seconds,
            logger=context.logger,
        )
        context.logger.emit(
            "asset_replaced",
            theme=candidate.theme_title,
            group_key=candidate.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            transformation_target_id=prepared.transformation_target_id,
            source_asset_id=source_asset_id,
            output_sha256=prepared.output_sha256,
            alt_text=prepared.alt_text,
            cleanup=cleanup,
        )
        return _CandidateOutcome(
            candidate,
            "replaced",
            "apply",
            prepared=prepared,
            source_asset_id=source_asset_id,
            cleanup=cleanup,
        )
    except CandidateStale as exc:
        reason = _safe_exception(exc)
        context.logger.emit(
            "asset_stale",
            level="warning",
            theme=candidate.theme_title,
            group_key=candidate.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            stage="apply",
            reason=reason,
        )
        return _CandidateOutcome(
            candidate,
            "stale",
            "apply",
            prepared=prepared,
            error=reason,
        )
    except (McpCallError, httpx.HTTPError, OSError, PipelineError) as exc:
        reason = _safe_exception(exc)
        context.logger.emit(
            "asset_error",
            level="error",
            theme=candidate.theme_title,
            group_key=candidate.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            stage="apply",
            reason=reason,
        )
        return _CandidateOutcome(
            candidate,
            "error",
            "apply",
            prepared=prepared,
            error=reason,
        )


def _process_problem_unit(
    context: _ProcessingContext,
    candidates: tuple[AssetCandidate, ...],
) -> tuple[_CandidateOutcome, ...]:
    """Process every asset of one problem sequentially inside one worker."""

    return tuple(_process_candidate(context, candidate) for candidate in candidates)


def _problem_units(
    candidates: Sequence[AssetCandidate],
) -> tuple[tuple[AssetCandidate, ...], ...]:
    """Group ordered asset candidates by their source problem identity."""

    by_problem: dict[str, list[AssetCandidate]] = {}
    for candidate in candidates:
        by_problem.setdefault(candidate.problem_id, []).append(candidate)
    return tuple(tuple(values) for values in by_problem.values())


def _problem_batches(
    candidates: Sequence[AssetCandidate], batch_size: int
) -> Iterator[list[AssetCandidate]]:
    """Yield batches containing all assets for at most *batch_size* problems."""

    by_problem: dict[str, list[AssetCandidate]] = {}
    order: list[str] = []
    for candidate in candidates:
        if candidate.problem_id not in by_problem:
            order.append(candidate.problem_id)
            by_problem[candidate.problem_id] = []
        by_problem[candidate.problem_id].append(candidate)
    for problem_chunk in _chunks(order, batch_size):
        yield [candidate for problem_id in problem_chunk for candidate in by_problem[problem_id]]


def _assert_locked_inputs(
    *,
    converter_path: Path,
    converter_fingerprint: str,
    template_path: Path,
    template_fingerprint: str,
) -> None:
    """Stop if converter code or its SVG template changes during the run."""

    if _sha256_file(converter_path) != converter_fingerprint:
        raise PipelineError("converter file changed during the run")
    if _sha256_file(template_path) != template_fingerprint:
        raise PipelineError("SVG template changed during the run")


def _new_totals() -> Counter[str]:
    """Return an empty run counter with documented keys populated lazily."""

    return Counter()


def build_run_worklist(
    client: McpClient,
    *,
    catalog_snapshot_id: str,
    source_site_id: str,
    category_key: str,
    category_title: str,
    theme_titles: Sequence[str],
    mode: str,
    converter_fingerprint: str,
    template_fingerprint: str,
    scope: Sequence[tuple[ThemeScope, list[GroupScope]]],
    run_dir: Path,
    logger: EventLogger,
) -> tuple[dict[str, GroupInventory], Counter[str]]:
    """Resolve every target once and persist the immutable ordered run worklist."""

    manifest: dict[str, Any] = {
        "catalog_snapshot_id": catalog_snapshot_id,
        "source_site_id": source_site_id,
        "category_key": category_key,
        "category_title": category_title,
        "theme_titles": list(theme_titles),
        "mode": mode,
        "converter_sha256": converter_fingerprint,
        "template_sha256": template_fingerprint,
        "groups": [],
    }
    inventory_by_group: dict[str, GroupInventory] = {}
    ordered_candidates: list[AssetCandidate] = []
    totals = _new_totals()
    seen_candidate_keys: set[str] = set()
    manifest_path = run_dir / "inventory.json"

    total_group_count = sum(len(groups) for _, groups in scope)
    logger.emit(
        "worklist_build_start",
        themes=len(scope),
        groups=total_group_count,
    )
    group_position = 0
    for theme, groups in scope:
        for group in groups:
            group_position += 1
            logger.emit(
                "worklist_group_scan_start",
                theme=theme.title,
                group_key=group.group_key,
                source_group_id=group.source_group_id,
                position=group_position,
                total_groups=total_group_count,
            )
            inventory = build_group_inventory(
                client,
                catalog_snapshot_id=catalog_snapshot_id,
                theme=theme,
                group=group,
            )
            if group.source_group_id in inventory_by_group:
                raise PipelineError(f"duplicate worklist group {group.source_group_id}")
            inventory_by_group[group.source_group_id] = inventory
            manifest["groups"].append(inventory.manifest_payload())
            _atomic_write_json(manifest_path, manifest)
            totals["groups"] += 1
            totals["inventory_png_tasks"] += inventory.counts.get("png_tasks", 0)
            totals["inventory_png_assets"] += inventory.counts.get("png_assets", 0)
            totals["inventory_non_svg_assets"] += inventory.counts.get(
                "ordinary_non_svg_assets", 0
            )
            for candidate in inventory.candidates:
                if candidate.stable_key in seen_candidate_keys:
                    raise PipelineError(
                        f"duplicate worklist candidate {candidate.stable_key}"
                    )
                seen_candidate_keys.add(candidate.stable_key)
                ordered_candidates.append(candidate)
            logger.emit(
                "worklist_group_scanned",
                theme=theme.title,
                group_key=group.group_key,
                source_group_id=group.source_group_id,
                position=group_position,
                total_groups=total_group_count,
                tasks=inventory.counts.get("png_tasks", 0),
                assets=inventory.counts.get("png_assets", 0),
            )

    target_payloads = [asdict(candidate) for candidate in ordered_candidates]
    worklist_basis = json.dumps(
        target_payloads,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    worklist_payload = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "catalog_snapshot_id": catalog_snapshot_id,
        "source_site_id": source_site_id,
        "category_key": category_key,
        "theme_titles": list(theme_titles),
        "converter_sha256": converter_fingerprint,
        "template_sha256": template_fingerprint,
        "group_count": len(inventory_by_group),
        "problem_count": len({candidate.problem_id for candidate in ordered_candidates}),
        "target_count": len(ordered_candidates),
        "worklist_sha256": _sha256_bytes(worklist_basis),
        "targets": target_payloads,
    }
    _atomic_write_json(run_dir / "worklist.json", worklist_payload)
    logger.emit(
        "worklist_ready",
        groups=worklist_payload["group_count"],
        tasks=worklist_payload["problem_count"],
        assets=worklist_payload["target_count"],
        worklist_sha256=worklist_payload["worklist_sha256"],
    )
    return inventory_by_group, totals


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    """Read one required JSON object or fail with a bounded local error."""

    if not path.is_file():
        raise PipelineError(f"{label} is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"{label} is invalid: {_safe_exception(exc)}") from exc
    if not isinstance(payload, dict):
        raise PipelineError(f"{label} must be a JSON object")
    return payload


def _read_run_events(run_dir: Path) -> list[dict[str, Any]]:
    """Read every structured event from one immutable source run."""

    path = run_dir / "events.jsonl"
    if not path.is_file():
        raise PipelineError(f"source events are missing: {path}")
    events: list[dict[str, Any]] = []
    try:
        for line_number, raw_line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not raw_line.strip():
                continue
            event = json.loads(raw_line)
            if not isinstance(event, dict):
                raise PipelineError(
                    f"source event line {line_number} is not a JSON object"
                )
            events.append(event)
    except json.JSONDecodeError as exc:
        raise PipelineError(
            f"source events contain invalid JSON: {_safe_exception(exc)}"
        ) from exc
    if not events:
        raise PipelineError("source events are empty")
    return events


def _validated_source_run_dir(source_run_dir: Path, run_dir: Path) -> Path:
    """Resolve a distinct existing source run directory."""

    source = source_run_dir.resolve()
    if not source.is_dir():
        raise PipelineError(f"resume source run does not exist: {source}")
    if source == run_dir:
        raise PipelineError("--resume-from-run must differ from --run-dir")
    return source


def _load_validated_worklist(
    *,
    source_run_dir: Path,
    run_dir: Path,
    catalog_snapshot_id: str,
    source_site_id: str,
    category_key: str,
    theme_titles: Sequence[str],
    scope: Sequence[tuple[ThemeScope, list[GroupScope]]],
) -> tuple[dict[str, GroupInventory], dict[str, Any]]:
    """Load and fail-closed validate one fixed-scope immutable worklist."""

    source = _validated_source_run_dir(source_run_dir, run_dir)
    payload = _read_json_object(source / "worklist.json", label="source worklist")
    if payload.get("schema_version") != 1:
        raise PipelineError("source worklist schema_version must be 1")
    expected_header = {
        "catalog_snapshot_id": catalog_snapshot_id,
        "source_site_id": source_site_id,
        "category_key": category_key,
        "theme_titles": list(theme_titles),
    }
    for field_name, expected_value in expected_header.items():
        if payload.get(field_name) != expected_value:
            raise PipelineError(
                f"source worklist {field_name} does not match the requested scope"
            )
    raw_targets = payload.get("targets")
    if not isinstance(raw_targets, list):
        raise PipelineError("source worklist targets must be a list")
    worklist_basis = json.dumps(
        raw_targets,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    worklist_sha256 = _sha256_bytes(worklist_basis)
    if payload.get("worklist_sha256") != worklist_sha256:
        raise PipelineError("source worklist SHA-256 does not match its targets")

    expected_groups = {
        group.source_group_id: (theme, group)
        for theme, groups in scope
        for group in groups
    }
    if int(payload.get("group_count") or -1) != len(expected_groups):
        raise PipelineError("source worklist group_count does not match fixed scope")
    candidate_fields = set(AssetCandidate.__dataclass_fields__)
    candidates_by_group: dict[str, list[AssetCandidate]] = {
        group_id: [] for group_id in expected_groups
    }
    seen_keys: set[str] = set()
    for position, raw_target in enumerate(raw_targets, start=1):
        if not isinstance(raw_target, dict) or set(raw_target) != candidate_fields:
            raise PipelineError(f"source worklist target {position} has invalid fields")
        string_fields = candidate_fields - {
            "theme_order_index",
            "group_order_index",
            "problem_order_index",
            "sections",
            "expected_vertices",
        }
        if any(
            not isinstance(raw_target.get(field_name), str)
            or not str(raw_target[field_name]).strip()
            for field_name in string_fields
        ):
            raise PipelineError(f"source worklist target {position} has invalid strings")
        for field_name in (
            "theme_order_index",
            "group_order_index",
            "problem_order_index",
            "expected_vertices",
        ):
            if not isinstance(raw_target.get(field_name), int) or isinstance(
                raw_target.get(field_name), bool
            ):
                raise PipelineError(
                    f"source worklist target {position} has invalid {field_name}"
                )
        sections = raw_target.get("sections")
        if (
            not isinstance(sections, list)
            or not sections
            or any(section not in {"condition", "solution"} for section in sections)
        ):
            raise PipelineError(f"source worklist target {position} has invalid sections")
        candidate_payload = dict(raw_target)
        candidate_payload["sections"] = tuple(sections)
        candidate = AssetCandidate(**candidate_payload)
        try:
            UUID(candidate.problem_id)
        except ValueError as exc:
            raise PipelineError(
                f"source worklist target {position} has invalid problem_id"
            ) from exc
        expected = expected_groups.get(candidate.source_group_id)
        if expected is None:
            raise PipelineError(
                f"source worklist target {position} escaped fixed source groups"
            )
        theme, group = expected
        exact_scope = (
            candidate.theme_title == theme.title
            and candidate.snapshot_theme_id == theme.snapshot_theme_id
            and candidate.theme_order_index == theme.order_index
            and candidate.group_key == group.group_key
            and candidate.group_order_index == group.order_index
            and candidate.expected_vertices == theme.expected_vertices
        )
        if not exact_scope:
            raise PipelineError(
                f"source worklist target {position} does not match fixed group metadata"
            )
        if candidate.stable_key in seen_keys:
            raise PipelineError(
                f"source worklist contains duplicate target {candidate.stable_key}"
            )
        seen_keys.add(candidate.stable_key)
        candidates_by_group[candidate.source_group_id].append(candidate)

    if int(payload.get("target_count") or -1) != len(seen_keys):
        raise PipelineError("source worklist target_count does not match targets")
    problem_count = len(
        {
            candidate.problem_id
            for candidates in candidates_by_group.values()
            for candidate in candidates
        }
    )
    if int(payload.get("problem_count") or -1) != problem_count:
        raise PipelineError("source worklist problem_count does not match targets")

    inventory_by_group: dict[str, GroupInventory] = {}
    for source_group_id, (theme, group) in expected_groups.items():
        candidates = candidates_by_group[source_group_id]
        problem_ids = list(dict.fromkeys(candidate.problem_id for candidate in candidates))
        source_problem_ids = list(
            dict.fromkeys(candidate.source_problem_id for candidate in candidates)
        )
        inventory_by_group[source_group_id] = GroupInventory(
            theme_title=theme.title,
            snapshot_theme_id=theme.snapshot_theme_id,
            source_group_id=source_group_id,
            group_key=group.group_key,
            group_order_index=group.order_index,
            counts={
                "png_tasks": len(problem_ids),
                "png_assets": len(candidates),
                "ordinary_non_svg_assets": len(candidates),
            },
            non_svg_content_types={PNG_CONTENT_TYPE: len(candidates)},
            png_problem_ids=problem_ids,
            png_source_problem_ids=source_problem_ids,
            candidates=candidates,
        )
    _atomic_write_json(run_dir / "worklist.json", payload)
    return inventory_by_group, payload


def _event_candidate_key(
    event: dict[str, Any],
    *,
    candidates_by_key: dict[str, AssetCandidate],
    candidates_by_source_key: dict[tuple[str, str], list[AssetCandidate]],
) -> str | None:
    """Resolve one historical event to an exact immutable worklist target."""

    problem_id = str(event.get("problem_id") or "")
    asset_key = str(event.get("asset_key") or "")
    if problem_id and asset_key:
        key = f"{problem_id}:{asset_key}"
        return key if key in candidates_by_key else None
    source_problem_id = str(event.get("source_problem_id") or "")
    matches = candidates_by_source_key.get((source_problem_id, asset_key), [])
    event_group_key = str(event.get("group_key") or "")
    event_theme = str(event.get("theme") or "")
    if event_group_key:
        matches = [candidate for candidate in matches if candidate.group_key == event_group_key]
    if event_theme:
        matches = [
            candidate for candidate in matches if candidate.theme_title == event_theme
        ]
    return matches[0].stable_key if len(matches) == 1 else None


def _resume_inventory_from_run(
    *,
    source_run_dir: Path,
    run_dir: Path,
    catalog_snapshot_id: str,
    source_site_id: str,
    category_key: str,
    theme_titles: Sequence[str],
    scope: Sequence[tuple[ThemeScope, list[GroupScope]]],
    converter_fingerprint: str,
    template_fingerprint: str,
    preserve_applied: bool = False,
    logger: EventLogger,
) -> tuple[dict[str, GroupInventory], Counter[str]]:
    """Filter a validated worklist using terminal outcomes from a prior run."""

    source = _validated_source_run_dir(source_run_dir, run_dir)
    inventory_by_group, worklist = _load_validated_worklist(
        source_run_dir=source,
        run_dir=run_dir,
        catalog_snapshot_id=catalog_snapshot_id,
        source_site_id=source_site_id,
        category_key=category_key,
        theme_titles=theme_titles,
        scope=scope,
    )
    events = _read_run_events(source)
    run_starts = [event for event in events if event.get("event") == "run_start"]
    if len(run_starts) != 1:
        raise PipelineError("source run must contain exactly one run_start event")
    source_start = run_starts[0]
    source_converter = str(
        worklist.get("converter_sha256") or source_start.get("converter_sha256") or ""
    )
    source_template = str(
        worklist.get("template_sha256") or source_start.get("template_sha256") or ""
    )
    if not source_converter or not source_template:
        raise PipelineError("source run has no converter/template fingerprints")
    same_renderer = (
        source_converter == converter_fingerprint
        and source_template == template_fingerprint
    )
    all_candidates = [
        candidate
        for inventory in inventory_by_group.values()
        for candidate in inventory.candidates
    ]
    candidates_by_key = {candidate.stable_key: candidate for candidate in all_candidates}
    candidates_by_source_key: dict[tuple[str, str], list[AssetCandidate]] = {}
    for candidate in all_candidates:
        candidates_by_source_key.setdefault(
            (candidate.source_problem_id, candidate.asset_key), []
        ).append(candidate)

    terminal_by_key: dict[str, str] = {}
    for event in events:
        event_name = str(event.get("event") or "")
        key = _event_candidate_key(
            event,
            candidates_by_key=candidates_by_key,
            candidates_by_source_key=candidates_by_source_key,
        )
        if key is None:
            continue
        if event_name == "asset_replaced":
            terminal_by_key[key] = "applied"
        elif event_name == "asset_rejected":
            terminal_by_key[key] = "rejected"
        elif event_name == "asset_stale":
            terminal_by_key[key] = "stale"
        elif event_name == "asset_error":
            reason = str(event.get("reason") or "")
            missing_source = (
                event.get("stage") == "prepare"
                and "/problem-assets/" in reason
                and ("404 Not Found" in reason or "410 Gone" in reason)
            )
            terminal_by_key[key] = "missing_source" if missing_source else "error"

    skip_reason_by_key: dict[str, str] = {}
    for key, terminal in terminal_by_key.items():
        if terminal in {"missing_source", "stale"}:
            skip_reason_by_key[key] = terminal
        elif terminal == "applied" and (same_renderer or preserve_applied):
            skip_reason_by_key[key] = terminal
        elif terminal == "rejected" and same_renderer:
            skip_reason_by_key[key] = terminal

    totals = _new_totals()
    totals["groups"] = len(inventory_by_group)
    totals["inventory_png_tasks"] = int(worklist["problem_count"])
    totals["inventory_png_assets"] = int(worklist["target_count"])
    totals["inventory_non_svg_assets"] = int(worklist["target_count"])
    for inventory in inventory_by_group.values():
        original_candidates = inventory.candidates
        inventory.candidates = [
            candidate
            for candidate in original_candidates
            if candidate.stable_key not in skip_reason_by_key
        ]
        inventory.counts["resume_original_png_tasks"] = inventory.counts["png_tasks"]
        inventory.counts["resume_original_png_assets"] = inventory.counts["png_assets"]
        inventory.png_problem_ids = list(
            dict.fromkeys(candidate.problem_id for candidate in inventory.candidates)
        )
        inventory.png_source_problem_ids = list(
            dict.fromkeys(candidate.source_problem_id for candidate in inventory.candidates)
        )
        inventory.counts["png_tasks"] = len(inventory.png_problem_ids)
        inventory.counts["png_assets"] = len(inventory.candidates)
        inventory.counts["ordinary_non_svg_assets"] = len(inventory.candidates)
        inventory.non_svg_content_types = {PNG_CONTENT_TYPE: len(inventory.candidates)}

    reason_counts = Counter(skip_reason_by_key.values())
    remaining_candidates = [
        candidate
        for inventory in inventory_by_group.values()
        for candidate in inventory.candidates
    ]
    remaining_problem_count = len(
        {candidate.problem_id for candidate in remaining_candidates}
    )
    totals["resume_skipped_applied"] = reason_counts["applied"]
    totals["resume_skipped_rejected_same_renderer"] = reason_counts["rejected"]
    totals["resume_skipped_missing_source"] = reason_counts["missing_source"]
    totals["resume_skipped_stale"] = reason_counts["stale"]
    totals["resume_remaining_assets"] = len(remaining_candidates)
    totals["resume_remaining_tasks"] = remaining_problem_count
    resume_payload = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "source_run_dir": str(source),
        "source_worklist_sha256": worklist["worklist_sha256"],
        "source_converter_sha256": source_converter,
        "source_template_sha256": source_template,
        "current_converter_sha256": converter_fingerprint,
        "current_template_sha256": template_fingerprint,
        "same_renderer": same_renderer,
        "preserve_applied": preserve_applied,
        "remaining_task_count": remaining_problem_count,
        "remaining_target_count": len(remaining_candidates),
        "skip_counts": dict(sorted(reason_counts.items())),
    }
    _atomic_write_json(run_dir / "resume.json", resume_payload)
    logger.emit(
        "resume_ready",
        source_run_dir=str(source),
        same_renderer=same_renderer,
        preserve_applied=preserve_applied,
        tasks=remaining_problem_count,
        assets=len(remaining_candidates),
        applied=reason_counts["applied"],
        rejected=reason_counts["rejected"],
        missing=reason_counts["missing_source"],
        stale=reason_counts["stale"],
    )
    return inventory_by_group, totals


def _rollback_inventory_from_run(
    *,
    source_run_dir: Path,
    run_dir: Path,
    catalog_snapshot_id: str,
    source_site_id: str,
    category_key: str,
    theme_titles: Sequence[str],
    scope: Sequence[tuple[ThemeScope, list[GroupScope]]],
    logger: EventLogger,
) -> tuple[dict[str, list[RollbackCandidate]], Counter[str]]:
    """Build an exact guarded rollback list from successful source-run events."""

    source = _validated_source_run_dir(source_run_dir, run_dir)
    inventory_by_group, worklist = _load_validated_worklist(
        source_run_dir=source,
        run_dir=run_dir,
        catalog_snapshot_id=catalog_snapshot_id,
        source_site_id=source_site_id,
        category_key=category_key,
        theme_titles=theme_titles,
        scope=scope,
    )
    all_candidates = [
        candidate
        for inventory in inventory_by_group.values()
        for candidate in inventory.candidates
    ]
    candidates_by_key = {candidate.stable_key: candidate for candidate in all_candidates}
    candidates_by_source_key: dict[tuple[str, str], list[AssetCandidate]] = {}
    for candidate in all_candidates:
        candidates_by_source_key.setdefault(
            (candidate.source_problem_id, candidate.asset_key), []
        ).append(candidate)
    applied_by_key: dict[str, RollbackCandidate] = {}
    for event in _read_run_events(source):
        if event.get("event") != "asset_replaced":
            continue
        key = _event_candidate_key(
            event,
            candidates_by_key=candidates_by_key,
            candidates_by_source_key=candidates_by_source_key,
        )
        if key is None:
            raise PipelineError("asset_replaced event does not map to the worklist")
        candidate = candidates_by_key[key]
        if (
            str(event.get("theme") or "") != candidate.theme_title
            or str(event.get("group_key") or "") != candidate.group_key
            or str(event.get("source_problem_id") or "")
            != candidate.source_problem_id
        ):
            raise PipelineError("asset_replaced event escaped its worklist metadata")
        transformation_target_id = str(event.get("transformation_target_id") or "")
        source_asset_id = str(event.get("source_asset_id") or "")
        output_sha256 = str(event.get("output_sha256") or "").lower()
        if not transformation_target_id.startswith("asset:"):
            raise PipelineError("asset_replaced event has invalid transformation target")
        try:
            UUID(source_asset_id)
        except ValueError as exc:
            raise PipelineError("asset_replaced event has invalid source_asset_id") from exc
        if len(output_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in output_sha256
        ):
            raise PipelineError("asset_replaced event has invalid output SHA-256")
        applied_by_key[key] = RollbackCandidate(
            candidate=candidate,
            transformation_target_id=transformation_target_id,
            source_asset_id=source_asset_id,
            output_sha256=output_sha256,
        )

    rollback_by_group: dict[str, list[RollbackCandidate]] = {
        source_group_id: [] for source_group_id in inventory_by_group
    }
    for candidate in all_candidates:
        rollback_candidate = applied_by_key.get(candidate.stable_key)
        if rollback_candidate is not None:
            rollback_by_group[candidate.source_group_id].append(rollback_candidate)
    rollback_targets = [
        {
            **asdict(item.candidate),
            "transformation_target_id": item.transformation_target_id,
            "source_asset_id": item.source_asset_id,
            "output_sha256": item.output_sha256,
        }
        for source_group_id in rollback_by_group
        for item in rollback_by_group[source_group_id]
    ]
    rollback_payload = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "source_run_dir": str(source),
        "source_worklist_sha256": worklist["worklist_sha256"],
        "target_count": len(rollback_targets),
        "targets": rollback_targets,
    }
    _atomic_write_json(run_dir / "rollback.json", rollback_payload)
    totals = _new_totals()
    totals["groups"] = len(rollback_by_group)
    totals["rollback_targets"] = len(rollback_targets)
    logger.emit(
        "rollback_ready",
        source_run_dir=str(source),
        groups=len(rollback_by_group),
        tasks=len({item["problem_id"] for item in rollback_targets}),
        assets=len(rollback_targets),
    )
    return rollback_by_group, totals


def _rollback_batches(
    candidates: Sequence[RollbackCandidate], batch_size: int
) -> Iterator[list[RollbackCandidate]]:
    """Yield rollback batches containing at most *batch_size* problems."""

    by_problem: dict[str, list[RollbackCandidate]] = {}
    order: list[str] = []
    for item in candidates:
        problem_id = item.candidate.problem_id
        if problem_id not in by_problem:
            order.append(problem_id)
            by_problem[problem_id] = []
        by_problem[problem_id].append(item)
    for problem_chunk in _chunks(order, batch_size):
        yield [item for problem_id in problem_chunk for item in by_problem[problem_id]]


def _rollback_error_is_stale(exc: BaseException) -> bool:
    """Return whether rollback safely refused an absent or newer value."""

    reason = _safe_exception(exc).lower()
    return (
        "current problem transformation not found" in reason
        or "does not match expected_source_asset_id" in reason
    )


def _execute_rollback(
    client: McpClient,
    *,
    scope: Sequence[tuple[ThemeScope, list[GroupScope]]],
    rollback_by_group: dict[str, list[RollbackCandidate]],
    totals: Counter[str],
    args: argparse.Namespace,
    run_dir: Path,
    logger: EventLogger,
) -> tuple[int, int, bool]:
    """Delete exact historical transformations in bounded sequential batches."""

    global_tasks_seen = 0
    batches_seen = 0
    consecutive_asset_errors = 0
    stop_requested = False
    for theme, groups in scope:
        if stop_requested:
            break
        logger.emit(
            "theme_start",
            theme=theme.title,
            snapshot_theme_id=theme.snapshot_theme_id,
            groups=len(groups),
        )
        for group in groups:
            if stop_requested:
                break
            candidates = rollback_by_group[group.source_group_id]
            if not candidates:
                continue
            group_task_count = len(
                {item.candidate.problem_id for item in candidates}
            )
            logger.emit(
                "group_transition",
                theme=theme.title,
                group_key=group.group_key,
                source_group_id=group.source_group_id,
            )
            logger.emit(
                "group_opened",
                theme=theme.title,
                group_key=group.group_key,
                source_group_id=group.source_group_id,
                tasks=group_task_count,
                assets=len(candidates),
            )
            for local_batch_index, batch_candidates in enumerate(
                _rollback_batches(candidates, args.batch_size), start=1
            ):
                problem_order = list(
                    dict.fromkeys(
                        item.candidate.problem_id for item in batch_candidates
                    )
                )
                if args.max_tasks is not None:
                    remaining = args.max_tasks - global_tasks_seen
                    if remaining <= 0:
                        stop_requested = True
                        break
                    allowed_problem_ids = set(problem_order[:remaining])
                    batch_candidates = [
                        item
                        for item in batch_candidates
                        if item.candidate.problem_id in allowed_problem_ids
                    ]
                    problem_order = problem_order[:remaining]
                global_tasks_seen += len(problem_order)
                batches_seen += 1
                logger.emit(
                    "batch_start",
                    theme=theme.title,
                    group_key=group.group_key,
                    batch=batches_seen,
                    group_batch=local_batch_index,
                    tasks=len(problem_order),
                    assets=len(batch_candidates),
                    source_problem_ids=[
                        item.candidate.source_problem_id for item in batch_candidates
                    ],
                )
                rolled_back_in_batch = 0
                for item in batch_candidates:
                    candidate = item.candidate
                    totals["rollback_attempted"] += 1
                    try:
                        result = client.call(
                            "delete_problem_transformation",
                            {
                                "problem_id": candidate.problem_id,
                                "transformation_target_id": (
                                    item.transformation_target_id
                                ),
                                "expected_source_asset_id": item.source_asset_id,
                            },
                            attempts=1,
                        )
                        if (
                            str(result.get("problem_id") or "")
                            != candidate.problem_id
                            or str(
                                result.get("deleted_transformation_target_id")
                                or ""
                            )
                            != item.transformation_target_id
                        ):
                            raise PipelineError(
                                "rollback response does not match requested target"
                            )
                        rolled_back_in_batch += 1
                        totals["assets_rolled_back"] += 1
                        consecutive_asset_errors = 0
                        logger.emit(
                            "asset_rolled_back",
                            theme=theme.title,
                            group_key=group.group_key,
                            source_problem_id=candidate.source_problem_id,
                            problem_id=candidate.problem_id,
                            asset_key=candidate.asset_key,
                            transformation_target_id=item.transformation_target_id,
                            source_asset_id=item.source_asset_id,
                            output_sha256=item.output_sha256,
                            reopened_stages=result.get("reopened_stages", []),
                        )
                    except (McpCallError, httpx.HTTPError, OSError, PipelineError) as exc:
                        if _rollback_error_is_stale(exc):
                            totals["rollback_stale"] += 1
                            consecutive_asset_errors = 0
                            logger.emit(
                                "rollback_stale",
                                level="warning",
                                theme=theme.title,
                                group_key=group.group_key,
                                source_problem_id=candidate.source_problem_id,
                                problem_id=candidate.problem_id,
                                asset_key=candidate.asset_key,
                                reason=_safe_exception(exc),
                            )
                            continue
                        totals["asset_errors"] += 1
                        consecutive_asset_errors += 1
                        logger.emit(
                            "asset_error",
                            level="error",
                            theme=theme.title,
                            group_key=group.group_key,
                            source_problem_id=candidate.source_problem_id,
                            problem_id=candidate.problem_id,
                            asset_key=candidate.asset_key,
                            stage="rollback",
                            reason=_safe_exception(exc),
                        )
                        if (
                            args.max_asset_errors
                            and consecutive_asset_errors >= args.max_asset_errors
                        ):
                            raise PipelineError(
                                "maximum consecutive asset error count reached"
                            ) from exc
                logger.emit(
                    "batch_complete",
                    theme=theme.title,
                    group_key=group.group_key,
                    batch=batches_seen,
                    tasks=len(problem_order),
                    assets=len(batch_candidates),
                    rolled_back=rolled_back_in_batch,
                )
                _atomic_write_json(
                    run_dir / "progress.json",
                    {
                        "at": datetime.now(UTC).isoformat(),
                        "mode": "rollback",
                        "last_theme": theme.title,
                        "last_source_group_id": group.source_group_id,
                        "last_group_key": group.group_key,
                        "batches_seen": batches_seen,
                        "tasks_seen": global_tasks_seen,
                        "totals": dict(sorted(totals.items())),
                    },
                )
                if batch_candidates:
                    logger.emit(
                        "batch_pause",
                        theme=theme.title,
                        group_key=group.group_key,
                        batch=batches_seen,
                        seconds=args.batch_pause_seconds,
                    )
                    time.sleep(args.batch_pause_seconds)
                if (
                    args.stop_after_batches is not None
                    and batches_seen >= args.stop_after_batches
                ):
                    stop_requested = True
                if args.max_tasks is not None and global_tasks_seen >= args.max_tasks:
                    stop_requested = True
        logger.emit("theme_complete", theme=theme.title)
    return global_tasks_seen, batches_seen, stop_requested


def _validate_write_batch_policy(args: argparse.Namespace) -> None:
    """Require ten-task checkpoints and a bounded sliding worker window."""

    if args.batch_size != 10:
        raise PipelineError("write mode requires batches of 10")
    if not 1 <= getattr(args, "max_workers", 10) <= 10:
        raise PipelineError("write mode requires between 1 and 10 workers")


def run_pipeline(args: argparse.Namespace) -> int:
    """Run discovery, deterministic conversion, optional upload, and readback."""

    apply = args.mode == "apply"
    rollback = args.mode == "rollback"
    writes = apply or rollback
    run_dir = args.run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    logger = EventLogger(run_dir / "events.jsonl", color=args.color)
    client: McpClient | None = None
    summary: dict[str, Any] = {}
    try:
        if writes and args.confirm_catalog != args.catalog_snapshot_id:
            raise PipelineError(
                f"{args.mode} mode requires --confirm-catalog equal to "
                "--catalog-snapshot-id"
            )
        if writes:
            _validate_write_batch_policy(args)
        api_key = os.environ.get(args.api_key_env, "").strip()
        if not api_key:
            raise PipelineError(f"environment variable {args.api_key_env} is empty")
        converter_path = args.converter_path.resolve()
        template_path = args.template_path.resolve()
        if not converter_path.is_file() or not template_path.is_file():
            raise PipelineError("converter or SVG template file is missing")
        converter_fingerprint = _sha256_file(converter_path)
        template_fingerprint = _sha256_file(template_path)
        converter = _load_converter(converter_path)

        logger.emit(
            "run_start",
            status=args.mode,
            run_dir=str(run_dir),
            catalog_snapshot_id=args.catalog_snapshot_id,
            category_key=args.category_key,
            theme_titles=list(args.theme_titles),
            batch_size=args.batch_size,
            batch_pause_seconds=args.batch_pause_seconds,
            max_workers=args.max_workers,
            converter_sha256=converter_fingerprint,
            template_sha256=template_fingerprint,
            resume_from_run=(
                str(args.resume_from_run.resolve()) if args.resume_from_run else None
            ),
        )
        client = McpClient(
            url=args.mcp_url,
            api_key=api_key,
            timeout_seconds=args.mcp_timeout_seconds,
            logger=logger,
        )
        user_id = _validate_startup(client, mode=args.mode, logger=logger)
        source_site_id, scope = discover_catalog_scope(
            client,
            catalog_snapshot_id=args.catalog_snapshot_id,
            category_key=args.category_key,
            category_title=args.category_title,
            theme_titles=args.theme_titles,
            group_keys=args.group_keys,
            logger=logger,
        )
        if rollback:
            rollback_by_group, totals = _rollback_inventory_from_run(
                source_run_dir=args.resume_from_run,
                run_dir=run_dir,
                catalog_snapshot_id=args.catalog_snapshot_id,
                source_site_id=source_site_id,
                category_key=args.category_key,
                theme_titles=args.theme_titles,
                scope=scope,
                logger=logger,
            )
            global_tasks_seen, batches_seen, stop_requested = _execute_rollback(
                client,
                scope=scope,
                rollback_by_group=rollback_by_group,
                totals=totals,
                args=args,
                run_dir=run_dir,
                logger=logger,
            )
            status = "limited_complete" if stop_requested else "completed"
            if totals.get("rollback_stale"):
                status += "_with_skips"
            if totals.get("asset_errors"):
                status += "_with_errors"
            summary = {
                "at": datetime.now(UTC).isoformat(),
                "status": status,
                "mode": args.mode,
                "run_dir": str(run_dir),
                "source_run_dir": str(args.resume_from_run.resolve()),
                "user_id": user_id,
                "catalog_snapshot_id": args.catalog_snapshot_id,
                "source_site_id": source_site_id,
                "batches_seen": batches_seen,
                "tasks_seen": global_tasks_seen,
                "totals": dict(sorted(totals.items())),
            }
            _atomic_write_json(run_dir / "summary.json", summary)
            logger.emit("run_complete", status=status, **summary["totals"])
            return 0 if not totals.get("asset_errors") else 2

        if args.resume_from_run is not None:
            inventory_by_group, totals = _resume_inventory_from_run(
                source_run_dir=args.resume_from_run,
                run_dir=run_dir,
                catalog_snapshot_id=args.catalog_snapshot_id,
                source_site_id=source_site_id,
                category_key=args.category_key,
                theme_titles=args.theme_titles,
                scope=scope,
                converter_fingerprint=converter_fingerprint,
                template_fingerprint=template_fingerprint,
                preserve_applied=args.resume_preserve_applied,
                logger=logger,
            )
        else:
            inventory_by_group, totals = build_run_worklist(
                client,
                catalog_snapshot_id=args.catalog_snapshot_id,
                source_site_id=source_site_id,
                category_key=args.category_key,
                category_title=args.category_title,
                theme_titles=args.theme_titles,
                mode=args.mode,
                converter_fingerprint=converter_fingerprint,
                template_fingerprint=template_fingerprint,
                scope=scope,
                run_dir=run_dir,
                logger=logger,
            )
        consecutive_asset_errors = 0
        global_tasks_seen = 0
        batches_seen = 0
        determinism_verified = False
        determinism_gate = _DeterminismGate(
            converter=converter,
            template_path=template_path,
            run_dir=run_dir,
        )
        stop_requested = False

        processing_scope = [] if args.mode == "inventory" else scope
        for theme, groups in processing_scope:
            if stop_requested:
                break
            logger.emit(
                "theme_start",
                theme=theme.title,
                snapshot_theme_id=theme.snapshot_theme_id,
                groups=len(groups),
            )
            for group in groups:
                if stop_requested:
                    break
                logger.emit(
                    "group_transition",
                    theme=theme.title,
                    group_key=group.group_key,
                    source_group_id=group.source_group_id,
                )
                _assert_locked_inputs(
                    converter_path=converter_path,
                    converter_fingerprint=converter_fingerprint,
                    template_path=template_path,
                    template_fingerprint=template_fingerprint,
                )
                inventory = inventory_by_group[group.source_group_id]
                logger.emit(
                    "group_opened",
                    theme=theme.title,
                    group_key=group.group_key,
                    source_group_id=group.source_group_id,
                    tasks=inventory.counts.get("png_tasks", 0),
                    assets=inventory.counts.get("png_assets", 0),
                )
                logger.emit(
                    "group_inventory",
                    theme=theme.title,
                    group_key=group.group_key,
                    source_group_id=group.source_group_id,
                    tasks=inventory.counts.get("png_tasks", 0),
                    assets=inventory.counts.get("png_assets", 0),
                    counts=inventory.counts,
                    non_svg_content_types=inventory.non_svg_content_types,
                    source_problem_ids=inventory.png_source_problem_ids,
                )
                if not inventory.candidates:
                    continue

                if args.max_workers > 1:
                    problem_units = _problem_units(inventory.candidates)
                    if args.max_tasks is not None:
                        remaining_tasks = args.max_tasks - global_tasks_seen
                        if remaining_tasks <= 0:
                            stop_requested = True
                            break
                        problem_units = problem_units[:remaining_tasks]
                    if args.stop_after_batches is not None:
                        remaining_checkpoints = args.stop_after_batches - batches_seen
                        if remaining_checkpoints <= 0:
                            stop_requested = True
                            break
                        problem_units = problem_units[
                            : remaining_checkpoints * args.batch_size
                        ]
                    if not problem_units:
                        continue
                    logger.emit(
                        "worker_pool_start",
                        theme=theme.title,
                        group_key=group.group_key,
                        tasks=len(problem_units),
                        max_workers=args.max_workers,
                    )
                    processing_context = _ProcessingContext(
                        client=client,
                        source_site_id=source_site_id,
                        converter=converter,
                        converter_fingerprint=converter_fingerprint,
                        template_path=template_path,
                        run_dir=run_dir,
                        transfer_timeout_seconds=args.transfer_timeout_seconds,
                        logger=logger,
                        apply=apply,
                        determinism_gate=determinism_gate,
                    )
                    process_unit = partial(
                        _process_problem_unit,
                        processing_context,
                    )
                    preflight_outcomes: list[tuple[_CandidateOutcome, ...]] = []
                    remaining_units = problem_units
                    while remaining_units and not determinism_gate.verified:
                        preflight_outcomes.append(process_unit(remaining_units[0]))
                        remaining_units = remaining_units[1:]
                    problem_outcomes = (
                        *preflight_outcomes,
                        *_bounded_map_ordered(
                            remaining_units,
                            process_unit,
                            max_workers=args.max_workers,
                        ),
                    )
                    determinism_verified = (
                        determinism_verified or determinism_gate.verified
                    )
                    for checkpoint_start in range(
                        0,
                        len(problem_outcomes),
                        args.batch_size,
                    ):
                        checkpoint_units = problem_outcomes[
                            checkpoint_start : checkpoint_start + args.batch_size
                        ]
                        outcomes = tuple(
                            outcome
                            for unit_outcomes in checkpoint_units
                            for outcome in unit_outcomes
                        )
                        global_tasks_seen += len(checkpoint_units)
                        batches_seen += 1
                        prepared_count = 0
                        replaced_count = 0
                        for outcome in outcomes:
                            totals["assets_attempted"] += 1
                            if outcome.prepared is not None:
                                totals["assets_prepared"] += 1
                                prepared_count += 1
                            if outcome.status == "replaced":
                                totals["assets_replaced"] += 1
                                replaced_count += 1
                                consecutive_asset_errors = 0
                            elif outcome.status == "dry_run":
                                totals["assets_dry_run"] += 1
                                consecutive_asset_errors = 0
                            elif outcome.status == "stale":
                                totals["assets_stale"] += 1
                                consecutive_asset_errors = 0
                            elif outcome.status == "rejected":
                                totals["assets_rejected"] += 1
                                consecutive_asset_errors = 0
                            elif outcome.status == "error":
                                totals["asset_errors"] += 1
                                consecutive_asset_errors += 1
                        logger.emit(
                            "batch_complete",
                            theme=theme.title,
                            group_key=group.group_key,
                            batch=batches_seen,
                            tasks=len(checkpoint_units),
                            assets=len(outcomes),
                            prepared=prepared_count,
                            replaced=replaced_count,
                        )
                        _atomic_write_json(
                            run_dir / "progress.json",
                            {
                                "at": datetime.now(UTC).isoformat(),
                                "mode": args.mode,
                                "last_theme": theme.title,
                                "last_source_group_id": group.source_group_id,
                                "last_group_key": group.group_key,
                                "batches_seen": batches_seen,
                                "tasks_seen": global_tasks_seen,
                                "totals": dict(sorted(totals.items())),
                            },
                        )
                    if (
                        args.stop_after_batches is not None
                        and batches_seen >= args.stop_after_batches
                    ):
                        stop_requested = True
                    if (
                        args.max_tasks is not None
                        and global_tasks_seen >= args.max_tasks
                    ):
                        stop_requested = True
                    continue

                batches = list(_problem_batches(inventory.candidates, args.batch_size))
                for local_batch_index, batch_candidates in enumerate(batches, start=1):
                    if stop_requested:
                        break
                    problem_order = list(dict.fromkeys(c.problem_id for c in batch_candidates))
                    if args.max_tasks is not None:
                        remaining = args.max_tasks - global_tasks_seen
                        if remaining <= 0:
                            stop_requested = True
                            break
                        allowed_problem_ids = set(problem_order[:remaining])
                        batch_candidates = [
                            candidate
                            for candidate in batch_candidates
                            if candidate.problem_id in allowed_problem_ids
                        ]
                        problem_order = problem_order[:remaining]
                    global_tasks_seen += len(problem_order)
                    batches_seen += 1
                    logger.emit(
                        "batch_start",
                        theme=theme.title,
                        group_key=group.group_key,
                        batch=batches_seen,
                        group_batch=local_batch_index,
                        tasks=len(problem_order),
                        assets=len(batch_candidates),
                        source_problem_ids=list(
                            dict.fromkeys(c.source_problem_id for c in batch_candidates)
                        ),
                    )

                    prepared_assets: list[PreparedAsset] = []
                    for candidate in batch_candidates:
                        totals["assets_attempted"] += 1
                        try:
                            prepared = prepare_candidate(
                                client,
                                candidate=candidate,
                                converter=converter,
                                converter_fingerprint=converter_fingerprint,
                                template_path=template_path,
                                run_dir=run_dir,
                                transfer_timeout_seconds=args.transfer_timeout_seconds,
                                logger=logger,
                            )
                            if not determinism_verified:
                                verify_first_deterministic_render(
                                    prepared,
                                    converter=converter,
                                    template_path=template_path,
                                    run_dir=run_dir,
                                )
                                determinism_verified = True
                                logger.emit(
                                    "determinism_verified",
                                    source_problem_id=candidate.source_problem_id,
                                    asset_key=candidate.asset_key,
                                    output_sha256=prepared.output_sha256,
                                )
                            prepared_assets.append(prepared)
                            totals["assets_prepared"] += 1
                            consecutive_asset_errors = 0
                            logger.emit(
                                "asset_prepared",
                                theme=theme.title,
                                group_key=group.group_key,
                                source_problem_id=candidate.source_problem_id,
                                problem_id=candidate.problem_id,
                                asset_key=candidate.asset_key,
                                input_sha256=prepared.input_sha256,
                                output_sha256=prepared.output_sha256,
                                alt_text=prepared.alt_text,
                                validation=prepared.validation,
                                svg_path=str(prepared.svg_path),
                            )
                        except CandidateStale as exc:
                            totals["assets_stale"] += 1
                            consecutive_asset_errors = 0
                            logger.emit(
                                "asset_stale",
                                level="warning",
                                theme=theme.title,
                                group_key=group.group_key,
                                source_problem_id=candidate.source_problem_id,
                                problem_id=candidate.problem_id,
                                asset_key=candidate.asset_key,
                                reason=_safe_exception(exc),
                            )
                        except CandidateRejected as exc:
                            totals["assets_rejected"] += 1
                            consecutive_asset_errors = 0
                            logger.emit(
                                "asset_rejected",
                                level="warning",
                                theme=theme.title,
                                group_key=group.group_key,
                                source_problem_id=candidate.source_problem_id,
                                problem_id=candidate.problem_id,
                                asset_key=candidate.asset_key,
                                reason=_safe_exception(exc),
                            )
                        except (McpCallError, httpx.HTTPError, OSError) as exc:
                            totals["asset_errors"] += 1
                            consecutive_asset_errors += 1
                            logger.emit(
                                "asset_error",
                                level="error",
                                theme=theme.title,
                                group_key=group.group_key,
                                source_problem_id=candidate.source_problem_id,
                                problem_id=candidate.problem_id,
                                asset_key=candidate.asset_key,
                                stage="prepare",
                                reason=_safe_exception(exc),
                            )
                            if (
                                args.max_asset_errors
                                and consecutive_asset_errors >= args.max_asset_errors
                            ):
                                raise PipelineError(
                                    "maximum consecutive asset error count reached"
                                ) from exc

                    replaced_in_batch = 0
                    if apply:
                        for prepared in prepared_assets:
                            candidate = prepared.candidate
                            try:
                                source_asset_id, cleanup = apply_prepared_asset(
                                    client,
                                    source_site_id=source_site_id,
                                    prepared=prepared,
                                    transfer_timeout_seconds=args.transfer_timeout_seconds,
                                    logger=logger,
                                )
                                replaced_in_batch += 1
                                totals["assets_replaced"] += 1
                                consecutive_asset_errors = 0
                                logger.emit(
                                    "asset_replaced",
                                    theme=theme.title,
                                    group_key=group.group_key,
                                    source_problem_id=candidate.source_problem_id,
                                    problem_id=candidate.problem_id,
                                    asset_key=candidate.asset_key,
                                    transformation_target_id=prepared.transformation_target_id,
                                    source_asset_id=source_asset_id,
                                    output_sha256=prepared.output_sha256,
                                    alt_text=prepared.alt_text,
                                    cleanup=cleanup,
                                )
                            except CandidateStale as exc:
                                totals["assets_stale"] += 1
                                consecutive_asset_errors = 0
                                logger.emit(
                                    "asset_stale",
                                    level="warning",
                                    theme=theme.title,
                                    group_key=group.group_key,
                                    source_problem_id=candidate.source_problem_id,
                                    problem_id=candidate.problem_id,
                                    asset_key=candidate.asset_key,
                                    stage="apply",
                                    reason=_safe_exception(exc),
                                )
                            except (McpCallError, httpx.HTTPError, OSError, PipelineError) as exc:
                                totals["asset_errors"] += 1
                                consecutive_asset_errors += 1
                                logger.emit(
                                    "asset_error",
                                    level="error",
                                    theme=theme.title,
                                    group_key=group.group_key,
                                    source_problem_id=candidate.source_problem_id,
                                    problem_id=candidate.problem_id,
                                    asset_key=candidate.asset_key,
                                    stage="apply",
                                    reason=_safe_exception(exc),
                                )
                                if (
                                    args.max_asset_errors
                                    and consecutive_asset_errors
                                    >= args.max_asset_errors
                                ):
                                    raise PipelineError(
                                        "maximum consecutive asset error count reached"
                                    ) from exc
                    else:
                        totals["assets_dry_run"] += len(prepared_assets)

                    logger.emit(
                        "batch_complete",
                        theme=theme.title,
                        group_key=group.group_key,
                        batch=batches_seen,
                        tasks=len(problem_order),
                        assets=len(batch_candidates),
                        prepared=len(prepared_assets),
                        replaced=replaced_in_batch,
                    )
                    _atomic_write_json(
                        run_dir / "progress.json",
                        {
                            "at": datetime.now(UTC).isoformat(),
                            "mode": args.mode,
                            "last_theme": theme.title,
                            "last_source_group_id": group.source_group_id,
                            "last_group_key": group.group_key,
                            "batches_seen": batches_seen,
                            "tasks_seen": global_tasks_seen,
                            "totals": dict(sorted(totals.items())),
                        },
                    )
                    if apply and batch_candidates:
                        logger.emit(
                            "batch_pause",
                            theme=theme.title,
                            group_key=group.group_key,
                            batch=batches_seen,
                            seconds=args.batch_pause_seconds,
                        )
                        time.sleep(args.batch_pause_seconds)
                    if (
                        args.stop_after_batches is not None
                        and batches_seen >= args.stop_after_batches
                    ):
                        stop_requested = True
                    if args.max_tasks is not None and global_tasks_seen >= args.max_tasks:
                        stop_requested = True

            logger.emit("theme_complete", theme=theme.title)

        status = "completed"
        if stop_requested:
            status = "limited_complete"
        if totals.get("assets_rejected") or totals.get("assets_stale"):
            status += "_with_skips"
        if totals.get("asset_errors"):
            status += "_with_errors"
        summary = {
            "at": datetime.now(UTC).isoformat(),
            "status": status,
            "mode": args.mode,
            "run_dir": str(run_dir),
            "user_id": user_id,
            "catalog_snapshot_id": args.catalog_snapshot_id,
            "source_site_id": source_site_id,
            "converter_sha256": converter_fingerprint,
            "template_sha256": template_fingerprint,
            "determinism_verified": determinism_verified,
            "batches_seen": batches_seen,
            "tasks_seen": global_tasks_seen,
            "totals": dict(sorted(totals.items())),
        }
        _atomic_write_json(run_dir / "summary.json", summary)
        logger.emit("run_complete", status=status, **summary["totals"])
        return 0 if not totals.get("asset_errors") else 2
    except BaseException as exc:
        summary = {
            "at": datetime.now(UTC).isoformat(),
            "status": "failed",
            "mode": getattr(args, "mode", None),
            "run_dir": str(run_dir),
            "reason": _safe_exception(exc),
            "error_type": type(exc).__name__,
        }
        _atomic_write_json(run_dir / "summary.json", summary)
        logger.emit(
            "run_failed",
            level="error",
            status="failed",
            reason=summary["reason"],
            error_type=summary["error_type"],
        )
        return 1
    finally:
        if client is not None:
            client.close()
        logger.close()


def build_parser() -> argparse.ArgumentParser:
    """Build the inventory, dry-run, apply, and guarded rollback CLI."""

    script_dir = Path(__file__).resolve().parent
    default_run_dir = (
        Path(os.environ.get("SOLUTION_RUNNER_VAR_DIR", "var"))
        / "mcp-grid-polygon"
        / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    parser = argparse.ArgumentParser(
        description=(
            "Autonomously discover non-rejected grid-polygon PNGs, render SVG, "
            "and optionally attach exact target-scoped MCP transformations."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("inventory", "dry-run", "apply", "rollback"),
        default="dry-run",
    )
    parser.add_argument(
        "--mcp-url",
        default=os.environ.get("TEACHERHELPER_MCP_URL", DEFAULT_MCP_URL),
    )
    parser.add_argument("--api-key-env", default="TEACHERHELPER_MCP_API_KEY")
    parser.add_argument("--catalog-snapshot-id", default=DEFAULT_CATALOG_SNAPSHOT_ID)
    parser.add_argument("--confirm-catalog", default=None)
    parser.add_argument("--category-key", default=DEFAULT_CATEGORY_KEY)
    parser.add_argument("--category-title", default=DEFAULT_CATEGORY_TITLE)
    parser.add_argument(
        "--theme",
        action="append",
        dest="theme_titles",
        help="Exact theme title; repeat to override the four default themes.",
    )
    parser.add_argument(
        "--group-key",
        action="append",
        dest="group_keys",
        help="Exact configured source group key; repeat to select more than one group.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Ordered progress checkpoint size; apply mode requires 10.",
    )
    parser.add_argument("--batch-pause-seconds", type=float, default=0.0)
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum active problem chains in the sliding window (1..10).",
    )
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--stop-after-batches", type=int, default=None)
    parser.add_argument(
        "--max-asset-errors",
        type=int,
        default=0,
        help="Stop after this many consecutive errors; 0 keeps skipping and logging.",
    )
    parser.add_argument("--mcp-timeout-seconds", type=float, default=120.0)
    parser.add_argument("--transfer-timeout-seconds", type=float, default=120.0)
    parser.add_argument(
        "--color",
        choices=("auto", "always", "never"),
        default="auto",
        help="ANSI colors for console task-stage logs.",
    )
    parser.add_argument("--run-dir", type=Path, default=default_run_dir)
    parser.add_argument(
        "--resume-from-run",
        type=Path,
        default=None,
        help=(
            "Reuse and validate worklist.json/events.jsonl from a prior run. "
            "Required by rollback."
        ),
    )
    parser.add_argument(
        "--resume-preserve-applied",
        action="store_true",
        help=(
            "Keep successful replacements from the source run while retrying "
            "its rejected assets with a changed converter."
        ),
    )
    parser.add_argument(
        "--converter-path",
        type=Path,
        default=script_dir / "png_to_svg_by_contrast.py",
    )
    parser.add_argument(
        "--template-path",
        type=Path,
        default=script_dir / "template_from_lessons.svg",
    )
    return parser


def _validate_cli_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    """Reject ambiguous or unsafe local CLI combinations."""

    if args.theme_titles is None:
        args.theme_titles = list(DEFAULT_THEME_TITLES)
    if any(theme not in EXPECTED_VERTICES_BY_THEME for theme in args.theme_titles):
        parser.error(f"themes must be selected from {sorted(EXPECTED_VERTICES_BY_THEME)}")
    if args.group_keys is not None and len(set(args.group_keys)) != len(args.group_keys):
        parser.error("--group-key values must be unique")
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    if args.batch_pause_seconds < 0:
        parser.error("--batch-pause-seconds cannot be negative")
    if not 1 <= args.max_workers <= 10:
        parser.error("--max-workers must be between 1 and 10")
    if (
        args.mode in {"dry-run", "apply"}
        and args.max_workers > 1
        and args.batch_pause_seconds
    ):
        parser.error("concurrent mode requires --batch-pause-seconds 0")
    if (
        args.mode in {"dry-run", "apply"}
        and args.max_workers > 1
        and args.max_asset_errors
    ):
        parser.error("--max-asset-errors requires --max-workers 1")
    if args.max_tasks is not None and args.max_tasks <= 0:
        parser.error("--max-tasks must be positive")
    if args.stop_after_batches is not None and args.stop_after_batches <= 0:
        parser.error("--stop-after-batches must be positive")
    if args.max_asset_errors < 0:
        parser.error("--max-asset-errors cannot be negative")
    if args.mode == "rollback" and args.resume_from_run is None:
        parser.error("rollback mode requires --resume-from-run")
    if args.mode == "inventory" and args.resume_from_run is not None:
        parser.error("inventory mode cannot use --resume-from-run")
    if args.resume_preserve_applied and (
        args.mode != "apply" or args.resume_from_run is None
    ):
        parser.error(
            "--resume-preserve-applied requires apply mode and --resume-from-run"
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments and return the autonomous pipeline exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_cli_args(args, parser)
    return run_pipeline(args)


if __name__ == "__main__":
    sys.exit(main())
