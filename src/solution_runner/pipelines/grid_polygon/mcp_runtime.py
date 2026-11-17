"""Centralize narrow TeacherHelper MCP operations and retry semantics."""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from typing import Any

from .mcp_asset_operations import SOURCE_SITE_ID as _SOURCE_SITE_ID
from .mcp_asset_operations import AssetOperations
from .mcp_protocol import McpGateway as _McpGateway
from .mcp_transport import (
    HttpTransport,
    McpCallError,
    content_text,
    default_transport,
    unpack_result,
)

DEFAULT_MCP_URL = "https://lessons-helper.ru/mcp"
SOURCE_SITE_ID = _SOURCE_SITE_ID
McpGateway = _McpGateway


class JsonRpcMcpGateway(AssetOperations):
    """Call stateless TeacherHelper Streamable HTTP MCP through typed methods."""

    def __init__(
        self,
        *,
        url: str,
        api_key: str,
        timeout_seconds: float = 60.0,
        transport: HttpTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Create one sequential gateway with injectable transport and sleep."""

        self._url = url
        self._transport = transport or default_transport(
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )
        self._sleep = sleep
        self._next_id = 0

    def close(self) -> None:
        """Close the shared HTTP pool."""

        self._transport.close()

    def _call(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        read_only: bool,
    ) -> dict[str, Any]:
        """Call one tool with retry only when the operation is read-only."""

        attempts = 5 if read_only else 1
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            self._next_id += 1
            envelope = {
                "jsonrpc": "2.0",
                "id": self._next_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments or {}},
            }
            try:
                response = self._transport.post(self._url, json=envelope)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise McpCallError("MCP response is not a JSON object")
                if payload.get("error"):
                    raise McpCallError(
                        json.dumps(payload["error"], ensure_ascii=False)[:1000]
                    )
                result = payload.get("result")
                if not isinstance(result, dict):
                    raise McpCallError("MCP response has no result object")
                if result.get("isError"):
                    raise McpCallError(content_text(result) or "MCP tool failed")
                return unpack_result(result)
            except Exception as exc:  # noqa: BLE001 - transport implementations vary.
                last_error = exc
                if "Normalized content is unavailable" in str(exc):
                    break
                if attempt < attempts:
                    self._sleep(float(attempt))
        message = " ".join(str(last_error or "unknown error").split())[:1000]
        if not read_only:
            raise McpCallError(
                f"{name} returned an ambiguous write response; reconcile by readback: {message}"
            ) from last_error
        raise McpCallError(
            f"{name} failed after {attempts} attempts: {message}"
        ) from last_error

    def get_problem_context(self, problem_id: str) -> dict[str, Any]:
        """Return normalized problem transformation context."""

        return self._call(
            "get_problem_transformation_context",
            {"problem_id": problem_id},
            read_only=True,
        )

    def get_problem_batch(self, problem_ids: Sequence[str]) -> dict[str, Any]:
        """Return normalized content for one bounded problem batch."""

        if not 1 <= len(problem_ids) <= 30:
            raise ValueError("problem batch must contain 1 to 30 ids")
        return self._call(
            "get_problem_batch",
            {"problem_ids": list(problem_ids)},
            read_only=True,
        )

    def get_asset_metadata(self, asset_id: str) -> dict[str, Any]:
        """Return authoritative metadata for one current asset UUID."""

        return self._call(
            "get_asset",
            {"asset_id": asset_id},
            read_only=True,
        )

    def get_source_catalog_children(
        self,
        parent_id: str,
        parent_type: str,
    ) -> dict[str, Any]:
        """Return ordered children for one exact source parent."""

        return self._call(
            "get_source_catalog_children",
            {"parent_id": parent_id, "parent_type": parent_type},
            read_only=True,
        )

    def find_source_catalog_path(
        self,
        catalog_snapshot_id: str,
        source_id: str,
        target_type: str,
    ) -> dict[str, Any]:
        """Resolve one source id without retaining a group-specific UUID."""

        return self._call(
            "find_source_catalog_path",
            {
                "catalog_snapshot_id": catalog_snapshot_id,
                "query": source_id,
                "target_type": target_type,
            },
            read_only=True,
        )

    def get_source_catalog_section_images(
        self,
        target_id: str,
        target_type: str,
    ) -> dict[str, Any]:
        """Return compact current condition and solution image evidence."""

        return self._call(
            "get_source_catalog_section_images",
            {"target_id": target_id, "target_type": target_type},
            read_only=True,
        )

    def get_source_catalog_missing_solution_summary(
        self,
        target_id: str,
        target_type: str,
    ) -> dict[str, Any]:
        """Return current source identities whose solution is empty."""

        return self._call(
            "get_source_catalog_missing_solution_summary",
            {"target_id": target_id, "target_type": target_type},
            read_only=True,
        )

    def prepare_source_asset_upload(
        self,
        *,
        source_site_id: str,
        canonical_asset_key: str,
        content_type: str,
        byte_size: int,
        sha256: str,
    ) -> dict[str, Any]:
        """Create one source-asset upload target without blind retry."""

        return self._call(
            "prepare_source_asset_upload",
            {
                "source_site_id": source_site_id,
                "canonical_asset_key": canonical_asset_key,
                "content_type": content_type,
                "byte_size": byte_size,
                "sha256": sha256,
            },
            read_only=False,
        )

    def get_source_asset(self, source_asset_id: str) -> dict[str, Any]:
        """Return authoritative source-asset metadata."""

        return self._call(
            "get_source_asset",
            {"source_asset_id": source_asset_id},
            read_only=True,
        )

    def replace_condition_asset(
        self,
        target: Any,
        *,
        replacement_asset_id: str,
        alt_text: str,
    ) -> dict[str, str]:
        """Replace one condition target and require exact identity and alt readback."""

        target_id = f"asset:{target.asset_key}"
        return self.replace_problem_asset_target(
            problem_id=target.problem_id,
            transformation_target_id=target_id,
            replacement_asset_id=replacement_asset_id,
            alt_text=alt_text,
        )

    def replace_problem_asset_target(
        self,
        *,
        problem_id: str,
        transformation_target_id: str,
        replacement_asset_id: str,
        alt_text: str,
    ) -> dict[str, str]:
        """Replace one exact problem asset target and require matching readback."""

        self.get_problem_asset_target_context(problem_id, transformation_target_id)
        write_error: McpCallError | None = None
        try:
            self._call(
                "replace_problem_asset",
                {
                    "problem_id": problem_id,
                    "transformation_target_id": transformation_target_id,
                    "replacement_asset_id": replacement_asset_id,
                    "scope": "target",
                    "alt_text": alt_text,
                },
                read_only=False,
            )
        except McpCallError as exc:
            write_error = exc
        context = self.get_problem_asset_target_context(
            problem_id,
            transformation_target_id,
        )
        current = context.get("current_asset")
        current_asset_id = str(
            context.get("current_asset_id")
            or (current.get("asset_id") if isinstance(current, dict) else "")
            or ""
        )
        current_alt = str(current.get("alt") or "") if isinstance(current, dict) else ""
        if current_asset_id != replacement_asset_id or current_alt != alt_text:
            raise McpCallError("asset replacement readback differs") from write_error
        return {"asset_id": current_asset_id, "alt": current_alt}

    def apply_problem_transformations(
        self,
        problem_id: str,
        transformations: Sequence[dict[str, Any]],
    ) -> dict[str, Any]:
        """Apply one problem transformation batch without blind retry."""

        return self._call(
            "apply_problem_transformations_batch",
            {
                "problem_id": problem_id,
                "transformations": list(transformations),
            },
            read_only=False,
        )

    def attach_source_asset_to_problems(
        self,
        *,
        source_asset_id: str,
        section_id: str,
        alt_text: str,
        problem_ids: list[str],
    ) -> dict[str, Any]:
        """Attach one reusable SourceAsset to explicit solution sections."""

        return self._call(
            "attach_source_asset_to_problems",
            {
                "source_asset_id": source_asset_id,
                "section_id": section_id,
                "alt_text": alt_text,
                "problem_ids": problem_ids,
            },
            read_only=False,
        )

    def get_problem_asset_target_context(
        self,
        problem_id: str,
        transformation_target_id: str,
    ) -> dict[str, Any]:
        """Return authoritative problem asset-target readback."""

        return self._call(
            "get_problem_asset_target_context",
            {
                "problem_id": problem_id,
                "transformation_target_id": transformation_target_id,
            },
            read_only=True,
        )

    def get_problem_pipeline_state(self, problem_id: str) -> dict[str, Any]:
        """Return pipeline stage values and concurrency tokens."""

        return self._call(
            "get_problem_pipeline_state",
            {"problem_id": problem_id},
            read_only=True,
        )

    def reject_problem_content_pipeline(
        self, problem_id: str, reason: str
    ) -> dict[str, Any]:
        """Explicitly reject one problem without invoking a model or runner."""

        return self._call(
            "reject_problem_content_pipeline",
            {"problem_id": problem_id, "reason": reason},
            read_only=False,
        )

    def set_problem_pipeline_stage_state_batch(
        self,
        stage: str,
        updates: Sequence[dict[str, Any]],
        reason: str,
    ) -> dict[str, Any]:
        """Apply stage updates without blindly repeating an ambiguous write."""

        return self._call(
            "set_problem_pipeline_stage_state_batch",
            {"stage": stage, "updates": list(updates), "reason": reason},
            read_only=False,
        )
